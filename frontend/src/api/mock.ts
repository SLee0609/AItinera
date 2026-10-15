import type { DayPlan, Itinerary, ItineraryRequest, Stop } from "../types";

/** Development-only sample: a 3-day Paris trip by transit. Returned for any request. */

const stop = (placeId: string, name: string, description: string, visitMinutes: number, lat: number, lng: number): Stop => ({
  placeId,
  name,
  description,
  visitMinutes,
  location: { lat, lng },
});

const DAY_PLANS: DayPlan[] = [
  {
    day: 1,
    title: "Étoile & the Left Bank",
    stops: [
      stop("mock-arc", "Arc de Triomphe", "Napoleon's arch at the Étoile; climb to the roof for the Champs-Élysées view.", 60, 48.8738, 2.295),
      stop("mock-eiffel", "Eiffel Tower", "Gustave Eiffel's 1889 iron tower, with three visitor levels.", 120, 48.8584, 2.2945),
      stop("mock-orsay", "Musée d'Orsay", "Impressionist masterpieces inside a Beaux-Arts railway station.", 150, 48.86, 2.3266),
    ],
    legs: [{ durationMinutes: 18 }, { durationMinutes: 22 }],
    travelMinutes: 40,
  },
  {
    day: 2,
    title: "Louvre & the Islands",
    stops: [
      stop("mock-louvre", "Louvre Museum", "The world's most-visited museum and home of the Mona Lisa.", 180, 48.8606, 2.3376),
      stop("mock-chapelle", "Sainte-Chapelle", "Gothic chapel with 1,113 stained-glass panels.", 45, 48.8554, 2.345),
      stop("mock-notredame", "Notre-Dame", "The restored medieval cathedral on the Île de la Cité.", 60, 48.853, 2.3499),
      stop("mock-pantheon", "Panthéon & Luxembourg", "Neoclassical mausoleum, then a stroll in the Luxembourg Gardens.", 90, 48.8462, 2.3464),
    ],
    legs: [{ durationMinutes: 15 }, { durationMinutes: 6 }, { durationMinutes: 14 }],
    travelMinutes: 35,
  },
  {
    day: 3,
    title: "Montmartre to the Marais",
    stops: [
      stop("mock-sacrecoeur", "Sacré-Cœur", "Hilltop basilica above Montmartre's artists' square.", 120, 48.8867, 2.3431),
      stop("mock-canal", "Canal Saint-Martin", "Tree-lined locks and iron footbridges in the 10th.", 60, 48.871, 2.3657),
      stop("mock-pompidou", "Centre Pompidou", "Inside-out building with Europe's largest modern art collection.", 120, 48.8607, 2.3522),
      stop("mock-marais", "Le Marais", "Medieval lanes, galleries, falafel, and the Place des Vosges.", 90, 48.8556, 2.3655),
    ],
    legs: [{ durationMinutes: 24 }, { durationMinutes: 18 }, { durationMinutes: 12 }],
    travelMinutes: 54,
  },
];

export const SAMPLE_ITINERARY: Itinerary = {
  city: "Paris, France",
  travelMode: "TRANSIT",
  dayPlans: DAY_PLANS,
  optimizedTravelMinutes: 129,
  naiveTravelMinutes: 226,
};

export function mockItinerary(_request: ItineraryRequest, signal?: AbortSignal): Promise<Itinerary> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => resolve(structuredClone(SAMPLE_ITINERARY)), 900);
    signal?.addEventListener("abort", () => {
      clearTimeout(timer);
      reject(signal.reason);
    });
  });
}
