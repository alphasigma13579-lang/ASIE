type BrandMarkProps = {
  size?: "sm" | "md" | "lg";
  className?: string;
};

export function BrandMark({ size = "md", className = "" }: BrandMarkProps) {
  return (
    <span className={`brand-symbol brand-symbol--${size} ${className}`.trim()} aria-hidden="true">
      <img src="/asie-logo.png" alt="" />
    </span>
  );
}

export function BrandLockup({ subtitle, className = "", landing = false }: { subtitle: string; className?: string; landing?: boolean }) {
  return (
    <div className={`brand-lockup${landing ? " brand-lockup--landing" : ""} ${className}`.trim()} aria-label={`ASIE — ${subtitle}`}>
      <BrandMark />
      <div>
        <strong>ASIE</strong>
        <span>{subtitle}</span>
      </div>
    </div>
  );
}
