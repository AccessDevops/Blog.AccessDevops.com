<script setup lang="ts">
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '~/lib/utils';
const buttonVariants = cva('inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 disabled:opacity-50', {
  variants: {
    variant: { default: 'bg-primary text-primary-foreground hover:bg-primary/90', outline: 'border border-border hover:bg-muted', ghost: 'hover:bg-muted' },
    size: { default: 'h-9 px-4 py-2', sm: 'h-8 px-3', lg: 'h-11 px-6' },
  },
  defaultVariants: { variant: 'default', size: 'default' },
});
const props = defineProps<VariantProps<typeof buttonVariants> & { class?: string }>();
</script>
<template>
  <button :class="cn(buttonVariants({ variant: props.variant, size: props.size }), props.class)"><slot /></button>
</template>
