import { describe, expect, it } from "vitest";
import type { User } from "@supabase/supabase-js";
import { linkError, loginUrl, resetPasswordUrl, safeNext, saveAfterLoginPath } from "./auth";
import { tripUrl } from "./itinerary";
import { displayName, initials } from "../auth/context";

describe("safeNext", () => {
  it.each([
    ["/trip/abcdefghijkl?save=1", "/trip/abcdefghijkl?save=1"],
    ["/saved", "/saved"],
    [null, "/"],
    ["", "/"],
    ["https://evil.example/", "/"],
    ["//evil.example/", "/"],
    ["/\\evil.example", "/"],
    ["javascript:alert(1)", "/"],
  ])("%s -> %s", (next, out) => expect(safeNext(next)).toBe(out));
});

describe("loginUrl", () => {
  it("encodes next", () => expect(loginUrl("/trip/abc?save=1")).toBe("/login?next=%2Ftrip%2Fabc%3Fsave%3D1"));
  it("adds the sign-up mode", () => expect(loginUrl("/saved", "signup")).toBe("/login?next=%2Fsaved&mode=signup"));
  it("round-trips through safeNext", () => {
    const next = new URLSearchParams(loginUrl("/trip/abc?view=map&save=1").split("?")[1]).get("next");
    expect(safeNext(next)).toBe("/trip/abc?view=map&save=1");
  });
});

describe("saveAfterLoginPath", () => {
  it("adds the flag to a bare path", () => expect(saveAfterLoginPath("/trip/abc")).toBe("/trip/abc?save=1"));
  it("keeps existing parameters", () => expect(saveAfterLoginPath("/trip/abc?view=map")).toBe("/trip/abc?view=map&save=1"));
});

describe("tripUrl", () => {
  it("builds the share path", () => expect(tripUrl("Ab-_12345678")).toBe("/trip/Ab-_12345678"));
  it("keeps the map view only", () => {
    expect(tripUrl("abc", "map")).toBe("/trip/abc?view=map");
    expect(tripUrl("abc", "list")).toBe("/trip/abc");
  });
});

describe("initials and displayName", () => {
  const user = (meta: Record<string, unknown>, email?: string) => ({ user_metadata: meta, email }) as unknown as User;

  it.each([
    ["Alex Kim", "AK"],
    ["Alex Middle Kim", "AK"],
    ["alex", "A"],
    ["alex@example.com", "A"],
    ["", "?"],
  ])("%s -> %s", (name, out) => expect(initials(name)).toBe(out));

  it("prefers the Google name, then the email", () => {
    expect(displayName(user({ full_name: "Alex Kim" }, "a@x.com"))).toBe("Alex Kim");
    expect(displayName(user({ name: "Alex" }, "a@x.com"))).toBe("Alex");
    expect(displayName(user({}, "a@x.com"))).toBe("a@x.com");
    expect(displayName(user({ full_name: 42 }))).toBe("Account");
  });
});

describe("resetPasswordUrl", () => {
  it("carries next through the reset page", () => {
    const url = resetPasswordUrl("/trip/abc?save=1");
    expect(url).toBe("/reset-password?next=%2Ftrip%2Fabc%3Fsave%3D1");
    expect(safeNext(new URLSearchParams(url.split("?")[1]).get("next"))).toBe("/trip/abc?save=1");
  });
});

describe("linkError", () => {
  it("is null for a normal sign-in fragment", () => {
    expect(linkError("#access_token=x&type=recovery")).toBeNull();
    expect(linkError("")).toBeNull();
  });
  it("reads Supabase's description and ends it with a period", () =>
    expect(linkError("#error=access_denied&error_code=otp_expired&error_description=Email+link+is+invalid+or+has+expired")).toBe(
      "Email link is invalid or has expired.",
    ));
  it("falls back when there is no description", () =>
    expect(linkError("#error_code=otp_expired")).toBe("This link is invalid or has expired."));
});
