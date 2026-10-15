import { describe, expect, it } from "vitest";
import { formatTravel, formatVisit } from "./format";
import { parseDays, travelSavings, tripSearch } from "./itinerary";

describe("formatTravel", () => {
  it("uses minutes under an hour", () => expect(formatTravel(40)).toBe("40 min"));
  it("pads minutes past the hour", () => expect(formatTravel(129)).toBe("2h 09m"));
  it("rounds fractional minutes", () => expect(formatTravel(59.6)).toBe("1h 00m"));
});

describe("formatVisit", () => {
  it.each([
    [45, "45m"],
    [60, "1h"],
    [150, "2h 30m"],
  ])("%i minutes -> %s", (m, out) => expect(formatVisit(m)).toBe(out));
});

describe("travelSavings", () => {
  it("computes minutes and rounded percent", () => expect(travelSavings(129, 226)).toEqual({ minutes: 97, percent: 43 }));
  it("never reports negative savings", () => expect(travelSavings(80, 60)).toEqual({ minutes: 0, percent: 0 }));
  it("handles a zero baseline", () => expect(travelSavings(0, 0)).toEqual({ minutes: 0, percent: 0 }));
});

describe("parseDays", () => {
  it("accepts values in range", () => expect(parseDays("3")).toBe(3));
  it.each([null, "", "0", "8", "2.5", "abc", "-1"])("rejects %s", (v) => expect(parseDays(v)).toBeNull());
});

describe("tripSearch", () => {
  it("encodes the city", () => expect(tripSearch("New York", 5, "map")).toBe("/trip?city=New+York&days=5&view=map"));
});
