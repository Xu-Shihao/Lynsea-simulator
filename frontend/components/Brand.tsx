import Link from "next/link";

/** Material Symbols Outlined icon. */
export function Icon({
  name,
  className = "",
  fill = false,
  weight,
  style,
}: {
  name: string;
  className?: string;
  fill?: boolean;
  weight?: number;
  style?: React.CSSProperties;
}) {
  const settings: string[] = [];
  if (fill) settings.push("'FILL' 1");
  if (weight != null) settings.push(`'wght' ${weight}`);
  return (
    <span
      className={`material-symbols-outlined ${className}`}
      style={{
        ...(settings.length
          ? { fontVariationSettings: settings.join(", ") }
          : {}),
        ...style,
      }}
      aria-hidden
    >
      {name}
    </span>
  );
}

/** Wordmark used in headers (matches the Stitch `blur_circular` + Lynsea). */
export function Logo({
  className = "",
  size = "text-headline",
}: {
  className?: string;
  size?: string;
}) {
  return (
    <span
      className={`font-display ${size} font-bold text-primary tracking-tight flex items-center gap-sm ${className}`}
    >
      <Icon name="blur_circular" weight={300} />
      Lynsea
    </span>
  );
}

/**
 * Top app bar. The Console (input) page uses the marketing-style nav; the
 * results page passes `subtitle` for context. Kept as a single component so
 * both pages share the fixed navy bar from the Stitch design.
 */
export function Header({
  subtitle,
  active = "Console",
}: {
  subtitle?: string;
  active?: string;
}) {
  const links = ["Console", "Archive", "Observatory", "Models"];
  return (
    <nav className="sticky top-0 z-50 flex justify-between items-center px-lg h-16 bg-surface-dim/90 backdrop-blur-md border-b border-surface-variant">
      <div className="flex items-center gap-md">
        <Link href="/" className="focus-ring rounded-lg">
          <Logo />
        </Link>
        <div className="hidden md:flex items-center gap-lg ml-xl">
          {links.map((l) =>
            l === active ? (
              <span
                key={l}
                className="font-body text-body text-primary border-b-2 border-primary pb-1 font-medium"
              >
                {l}
              </span>
            ) : (
              <Link
                key={l}
                href="/"
                className="font-body text-body text-on-surface-variant hover:text-on-surface transition-colors duration-200"
              >
                {l}
              </Link>
            ),
          )}
        </div>
        {subtitle && (
          <span className="hidden lg:inline-block ml-md text-caption text-outline">
            {subtitle}
          </span>
        )}
      </div>
      <div className="flex items-center gap-md text-primary">
        <button
          type="button"
          className="hover:text-primary-fixed transition-colors opacity-80 hover:opacity-100"
          aria-label="Settings"
        >
          <Icon name="settings" />
        </button>
        <button
          type="button"
          className="hover:text-primary-fixed transition-colors opacity-80 hover:opacity-100"
          aria-label="Account"
        >
          <Icon name="account_circle" />
        </button>
      </div>
    </nav>
  );
}
