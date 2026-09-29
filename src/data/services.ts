/**
 * Service presentation metadata: the short label and hero image each service card
 * shows. Kept out of the Markdown because it is presentation, not prose — editing a
 * service's copy should never risk breaking its card image.
 */

export type ServiceMeta = {
  /** Short label for navigation and card eyebrows. */
  label: string;
  /** One-line summary used on cards when the page has no meta description. */
  blurb: string;
  image: string;
  icon: "droplet" | "gutter" | "spray" | "car" | "paint" | "moss";
};

export const services: Record<string, ServiceMeta> = {
  "window-washing": {
    label: "Window washing",
    blurb: "Streak-free glass inside and out, up to three storeys.",
    image: "/images/service-window-washing.webp",
    icon: "droplet",
  },
  "gutter-cleaning": {
    label: "Gutter cleaning",
    blurb: "Clear out the debris before it causes leaks and ice dams.",
    image: "/images/service-gutter-cleaning.webp",
    icon: "gutter",
  },
  "pressure-washing": {
    label: "Pressure washing",
    blurb: "Driveways, decks, siding and walkways back to like-new.",
    image: "/images/service-pressure-washing.webp",
    icon: "spray",
  },
  "automobile-detailing": {
    label: "Auto detailing",
    blurb: "Interior and exterior detail for cars and trucks.",
    image: "/images/service-detailing.webp",
    icon: "car",
  },
  "house-painting": {
    label: "House painting",
    blurb: "Interior and exterior painting that lasts through our winters.",
    image: "/images/service-painting.webp",
    icon: "paint",
  },
  "moss-removal": {
    label: "Roof moss removal",
    blurb: "Stop moss rotting your shingles and shortening the roof's life.",
    image: "/images/service-moss-removal.webp",
    icon: "moss",
  },
};
