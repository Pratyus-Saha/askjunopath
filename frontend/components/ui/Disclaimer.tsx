export default function Disclaimer({ text }: { text?: string }) {
  const defaultText = "AskJunoPath computes chart positions using Swiss Ephemeris and explains them using KP and Vedic astrology principles. Astrology's predictive accuracy is unproven. This is not professional advice.";
  const displayText = text ? text.replace('using KP astrology principles', 'using KP and Vedic astrology principles') : defaultText;

  return (
    <div className="text-sm text-[var(--muted-on-dark)] border border-[var(--border)] bg-[var(--navy-raised)] p-4 rounded-md">
      {displayText}
    </div>
  );
}
