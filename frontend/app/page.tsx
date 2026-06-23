import type { Metadata } from "next";
import Landing from "@/components/juno/Landing";

const DESCRIPTION =
  "JunoPath computes your birth chart to the arc-second and explains the reasoning behind every line. A precise instrument, not a horoscope.";

export const metadata: Metadata = {
  title: "JunoPath — The exact sky you were born under",
  description: DESCRIPTION,
  openGraph: {
    title: "JunoPath — Astrology, computed and explained",
    description: DESCRIPTION,
  },
};

export default function Page() {
  return <Landing />;
}
