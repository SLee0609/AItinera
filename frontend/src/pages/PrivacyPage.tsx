import type { ReactNode } from "react";
import { Link } from "react-router";
import AccountNav from "../components/AccountNav";
import Logo from "../components/Logo";

/** Where privacy questions and deletion requests go. Must be a mailbox someone reads. */
const CONTACT_EMAIL = "privacy@aitinera.org";
const EFFECTIVE_DATE = "October 16, 2026";

const SITE = "https://aitinera-app.vercel.app";

/** `/privacy`: the privacy policy, also linked from the Google sign-in consent screen. */
export default function PrivacyPage() {
  return (
    <div className="min-h-dvh bg-canvas">
      <header className="sticky top-0 z-20 flex items-center gap-7 border-b border-line bg-white px-4 py-3 sm:px-10 md:h-16 md:py-0">
        <Logo />
        <div className="ml-auto flex items-center gap-2.5">
          <Link to="/" className="rounded-[10px] bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-ink/85">
            Plan a trip
          </Link>
          <AccountNav />
        </div>
      </header>

      <main className="mx-auto max-w-[720px] px-4 pt-10 pb-20 sm:px-10">
        <h1 className="font-display text-[32px] font-bold tracking-tight">Privacy policy</h1>
        <p className="mt-1 text-sm text-sub">Effective {EFFECTIVE_DATE}</p>

        <div className="mt-8 grid gap-8 text-[15px] leading-relaxed">
          <p>
            AItinera ({SITE}) plans multi-day sightseeing itineraries. This policy explains what information we collect when you use
            AItinera, how we use it, and the choices you have. You can plan and share trips without an account; an account is needed only
            to save trips.
          </p>

          <Section title="Information we collect">
            <List>
              <li>
                <b>Trip requests.</b> The destination you enter and the number of days. Don't type personal information into the
                destination field.
              </li>
              <li>
                <b>Generated itineraries.</b> Every itinerary we generate is stored with a random ID so its share link keeps working. An
                itinerary contains the destination, attractions, visit times and travel times. If you're signed in when you generate it, we
                also record which account created it; this is never shown to people you share it with.
              </li>
              <li>
                <b>Account information.</b> If you create an account with email and password, we store your email address and a securely
                hashed password (we never see or store the password itself). If you sign in with Google, we receive your name, email address
                and profile picture URL from Google.
              </li>
              <li>
                <b>Saved itineraries.</b> Which itineraries you save, and when.
              </li>
              <li>
                <b>Technical information.</b> Our hosting and authentication providers keep standard server logs, which include IP
                addresses, browser type and the time and path of each request. We use these logs to keep the service working and secure.
              </li>
            </List>
            <p>
              We don't use advertising or analytics cookies, and we don't track you across other websites. When you're signed in, your
              browser's local storage keeps your sign-in session so you stay signed in.
            </p>
          </Section>

          <Section title="How we use information">
            <List>
              <li>To generate itineraries, show them to you, and keep share links working.</li>
              <li>To create and secure your account, sign you in, and send account emails such as the confirmation link.</li>
              <li>To show your saved itineraries.</li>
              <li>To diagnose problems, prevent abuse, and keep costs under control.</li>
            </List>
            <p>We don't sell your information, and we don't use it for advertising.</p>
          </Section>

          <Section title="Google user data">
            <p>
              If you sign in with Google, we request only your basic profile: name, email address and profile picture. We use it only to
              create your account, sign you in and show your name in the app. We don't request access to your Gmail, Drive, Calendar or any
              other Google data, and we don't share Google user data with anyone except the service providers listed below that run AItinera.
            </p>
            <p>
              AItinera's use and transfer of information received from Google APIs adheres to the{" "}
              <A href="https://developers.google.com/terms/api-services-user-data-policy">Google API Services User Data Policy</A>, including
              the Limited Use requirements.
            </p>
          </Section>

          <Section title="Sharing">
            <p>
              <b>Share links.</b> Anyone with an itinerary's link can view that itinerary. Itineraries don't include your name, email or
              account. Links use long random IDs that can't practically be guessed, but treat a link like the trip itself: anyone you give it
              to can pass it on.
            </p>
            <p>
              <b>Service providers.</b> We use these companies to run AItinera. Each receives only what it needs for its part:
            </p>
            <List>
              <li>
                <b>Supabase</b>: account sign-in and our database (accounts, itineraries, saved itineraries).
              </li>
              <li>
                <b>Vercel</b>: hosting for the website and its server.
              </li>
              <li>
                <b>Google</b>: Gemini suggests attractions from the destination and trip length; Google Maps Platform verifies places,
                provides travel times and displays the map; Google sign-in, if you choose it. No account information is sent to Gemini or
                Google Maps Platform.
              </li>
              <li>
                <b>Resend</b>: delivers account emails.
              </li>
            </List>
            <p>We may also disclose information if required by law, or to protect the rights and safety of our users or others.</p>
          </Section>

          <Section title="Retention and deletion">
            <List>
              <li>Account information and saved itineraries are kept until you delete your account.</li>
              <li>
                Generated itineraries are kept so their share links keep working. When an account is deleted, its saved list is deleted, and
                itineraries it created stay available only as anonymous share links.
              </li>
              <li>Server logs are kept for a limited time by our providers, as set by their own policies.</li>
            </List>
            <p>
              You can delete your account at any time from the account menu (Delete account). This immediately deletes your account
              information and your saved list. You can also remove individual trips from your saved list on the Saved itineraries page.
            </p>
            <p>
              To ask for a copy or correction of your information, or for help deleting your account, email{" "}
              <A href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</A> from the address on your account. We'll respond within 30 days.
            </p>
          </Section>

          <Section title="Security">
            <p>
              Connections to AItinera are encrypted (HTTPS). Passwords are hashed by our authentication provider, and our database is not
              accessible directly from the browser. No system is perfectly secure, but we work to protect your information.
            </p>
          </Section>

          <Section title="Children">
            <p>
              AItinera is not directed at children under 13, and we don't knowingly collect their information. If you believe a child has
              created an account, contact us and we'll delete it.
            </p>
          </Section>

          <Section title="Changes to this policy">
            <p>
              If we change this policy, we'll update it on this page and change the effective date above. For significant changes, we'll
              give notice in the app.
            </p>
          </Section>

          <Section title="Contact">
            <p>
              Questions about this policy or your information: <A href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</A>.
            </p>
          </Section>
        </div>
      </main>
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="grid gap-3">
      <h2 className="font-display text-xl font-bold tracking-tight">{title}</h2>
      {children}
    </section>
  );
}

function List({ children }: { children: ReactNode }) {
  return <ul className="grid list-disc gap-2 pl-5 marker:text-sub">{children}</ul>;
}

function A({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a href={href} className="font-medium text-accent underline underline-offset-2 hover:text-accent-hover">
      {children}
    </a>
  );
}
