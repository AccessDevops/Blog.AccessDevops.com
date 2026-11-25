#!/usr/bin/env python3
"""Mesure ce qu'un upload multipart interrompu laisse derrière lui.

Trois états intéressants, qui ne se voient pas au même endroit :

  1. le client meurt entre deux parts -> ListObjectsV2 ne voit rien (KeyCount 0),
     ListMultipartUploads voit l'upload, ListParts la somme des octets stockés ;
  2. la complétion est refusée (EntityTooSmall) -> l'objet n'existe pas, les parts
     restent, et les mêmes appels les retrouvent ;
  3. trois uploads en cours + MaxUploads=1 -> IsTruncated, un marqueur à suivre :
     une boucle qui lit la première page en rate la majorité.

Usage, contre un endpoint S3 local (SeaweedFS, MinIO, moto) :

    python3 scripts/incomplete-mpu-probe.py start http://127.0.0.1:18337
    python3 scripts/incomplete-mpu-probe.py abort http://127.0.0.1:18337

`start` laisse volontairement les uploads orphelins : c'est le sujet de la mesure.
"""
from __future__ import annotations

import sys

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

BUCKET = "mpu-leak-probe"
KEY = "backups/postgres/db-2026-11-25.tar"
MIB = 1024 * 1024
PART = 5 * MIB          # le plancher multipart, taille d'une part réelle
PARTS = 3               # 3 x 5 MiB : un dump interrompu tôt


def client(endpoint: str):
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id="probe",
        aws_secret_access_key="probe",
        region_name="us-east-1",
        config=Config(s3={"addressing_style": "path"}, signature_version="s3v4"),
    )


def cleanup(s3):
    try:
        s3.create_bucket(Bucket=BUCKET)
    except ClientError as exc:
        if exc.response["Error"]["Code"] not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            raise
    for u in s3.list_multipart_uploads(Bucket=BUCKET).get("Uploads", []):
        s3.abort_multipart_upload(Bucket=BUCKET, Key=u["Key"], UploadId=u["UploadId"])
    for obj in s3.list_objects_v2(Bucket=BUCKET).get("Contents", []):
        s3.delete_object(Bucket=BUCKET, Key=obj["Key"])


def state(s3, label: str):
    objs = s3.list_objects_v2(Bucket=BUCKET)
    uploads = s3.list_multipart_uploads(Bucket=BUCKET).get("Uploads", [])
    print(f"\n--- {label}")
    print(f"ListObjectsV2         KeyCount={objs.get('KeyCount', 0)}")
    print(f"ListMultipartUploads  {len(uploads)} upload(s) en cours")
    total = 0
    for u in uploads:
        parts = s3.list_parts(Bucket=BUCKET, Key=u["Key"], UploadId=u["UploadId"])
        sizes = [p["Size"] for p in parts.get("Parts", [])]
        total += sum(sizes)
        print(f"  key={u['Key']}  initiated={u['Initiated']}")
        print(f"  storage_class={u.get('StorageClass')}  initiator={u.get('Initiator')}")
        print(f"  ListParts {len(sizes)} part(s) {sizes} = {sum(sizes):,} octets")
    print(f"octets stockés en parts inachevées : {total:,}")
    return total


def start(endpoint: str):
    s3 = client(endpoint)
    cleanup(s3)

    # Cas 1 : le client meurt entre deux parts. Aucun abort, aucun complete.
    uid = s3.create_multipart_upload(Bucket=BUCKET, Key=KEY)["UploadId"]
    for n in range(1, PARTS + 1):
        s3.upload_part(Bucket=BUCKET, Key=KEY, UploadId=uid,
                       PartNumber=n, Body=b"\0" * PART)

    # Cas 2 : une complétion refusée. Le transfert a réussi, le serveur dit non.
    uid2 = s3.create_multipart_upload(Bucket=BUCKET, Key="backups/tiny.tar")["UploadId"]
    for n, size in ((1, MIB), (2, 1024)):       # part 1 sous le plancher de 5 MiB
        s3.upload_part(Bucket=BUCKET, Key="backups/tiny.tar", UploadId=uid2,
                       PartNumber=n, Body=b"\0" * size)
    etags = [{"PartNumber": p["PartNumber"], "ETag": p["ETag"]}
             for p in s3.list_parts(Bucket=BUCKET, Key="backups/tiny.tar",
                                    UploadId=uid2)["Parts"]]
    try:
        s3.complete_multipart_upload(Bucket=BUCKET, Key="backups/tiny.tar", UploadId=uid2,
                                     MultipartUpload={"Parts": etags})
        print("\n--- complétion acceptée (serveur sans plancher 5 MiB ?)")
    except ClientError as exc:
        err = exc.response["Error"]
        print(f"\n--- complétion refusée : {exc.response['ResponseMetadata']['HTTPStatusCode']} "
              f"{err['Code']} — {err['Message']!r}")

    total = state(s3, "après les deux échecs")

    # Cas 3 : la pagination. Trois uploads, une page d'un élément.
    for n in (1, 2, 3):
        s3.create_multipart_upload(Bucket=BUCKET, Key=f"backups/job-{n}.tar")
    page = s3.list_multipart_uploads(Bucket=BUCKET, MaxUploads=1)
    print(f"\n--- pagination : MaxUploads=1 -> IsTruncated={page.get('IsTruncated')} "
          f"NextKeyMarker={page.get('NextKeyMarker')!r}")

    # La règle de cycle de vie s'installe, mais sa granularité est le jour.
    s3.put_bucket_lifecycle_configuration(
        Bucket=BUCKET,
        LifecycleConfiguration={"Rules": [{
            "ID": "abort-incomplete", "Status": "Enabled",
            "Filter": {"Prefix": ""},
            "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 1},
        }]},
    )
    rules = s3.get_bucket_lifecycle_configuration(Bucket=BUCKET)["Rules"]
    abort_rule = rules[0].get("AbortIncompleteMultipartUpload", {})
    print(f"\n--- règle relue : {rules[0]['ID']} "
          f"DaysAfterInitiation={abort_rule.get('DaysAfterInitiation')}")
    state(s3, "règle posée : rien n'est supprimé dans la seconde")
    print(f"\ntotal mesuré avant nettoyage : {total:,} octets")


def abort(endpoint: str):
    s3 = client(endpoint)
    for u in s3.list_multipart_uploads(Bucket=BUCKET).get("Uploads", []):
        s3.abort_multipart_upload(Bucket=BUCKET, Key=u["Key"], UploadId=u["UploadId"])
    state(s3, "après abort de tous les uploads en cours")


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("start", "abort"):
        sys.exit(__doc__)
    (start if sys.argv[1] == "start" else abort)(sys.argv[2])
