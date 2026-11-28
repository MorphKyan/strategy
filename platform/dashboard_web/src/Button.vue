<script setup lang="ts">
import { cva } from 'class-variance-authority'
import { clsx, type ClassValue } from 'clsx'
import { Primitive } from 'reka-ui'
import { twMerge } from 'tailwind-merge'

const props = withDefaults(defineProps<{
  variant?: 'outline' | 'ghost'
  size?: 'default' | 'icon'
  class?: ClassValue
}>(), { variant: 'outline', size: 'default' })

// shadcn-vue Button, with the variants used by these two pages.
const variants = cva(
  'inline-flex shrink-0 cursor-pointer items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium transition-colors disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-4',
  {
    variants: {
      variant: {
        outline: 'border border-[var(--line)] bg-[var(--surface)] hover:bg-[var(--quiet)]',
        ghost: 'text-[var(--muted)] hover:bg-[var(--quiet)] hover:text-[var(--ink)]',
      },
      size: {
        default: 'h-9 px-3',
        icon: 'size-9',
      },
    },
  },
)
</script>

<template>
  <Primitive as="button" type="button" :class="twMerge(clsx(variants(props), props.class))">
    <slot />
  </Primitive>
</template>
