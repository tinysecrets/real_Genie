import * as React from "react"
import { cva } from "class-variance-authority";

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground shadow hover:bg-primary/80",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive:
          "border-transparent bg-destructive text-destructive-foreground shadow hover:bg-destructive/80",
        outline: "text-foreground",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

/**
 * Render a styled badge element whose visual style is selected by `variant`.
 *
 * @param {Object} props - Component props.
 * @param {string} [props.className] - Additional class names to merge with the computed variant classes.
 * @param {'default'|'secondary'|'destructive'|'outline'} [props.variant='default'] - Visual variant to apply.
 * @param {import('react').HTMLAttributes<HTMLDivElement>} [props.props] - Additional HTML attributes forwarded to the root div.
 * @returns {JSX.Element} A React element representing the badge.
 */
function Badge({
  className,
  variant,
  ...props
}) {
  return (<div className={cn(badgeVariants({ variant }), className)} {...props} />);
}

export { Badge, badgeVariants }
