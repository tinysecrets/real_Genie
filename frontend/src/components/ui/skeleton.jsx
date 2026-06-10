import { cn } from "@/lib/utils"

/**
 * Renders a div styled as a loading skeleton with pulsing animation.
 *
 * The component applies base classes `animate-pulse rounded-md bg-primary/10` and merges any
 * provided `className`. All other props are forwarded to the rendered div.
 *
 * @param {Object} props - Component props.
 * @param {string} [props.className] - Additional class names to merge with the base skeleton classes.
 * @param {...any} [props.*] - Additional attributes forwarded to the underlying div.
 * @returns {JSX.Element} A div element styled as a loading skeleton.
 */
function Skeleton({
  className,
  ...props
}) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-primary/10", className)}
      {...props} />
  );
}

export { Skeleton }
