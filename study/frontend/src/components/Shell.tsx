"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useContext } from "react";
import { post, useApi, type User } from "@/lib/api";

const UserContext = createContext<User | null>(null);

export function useUser(): User {
  return useContext(UserContext)!;
}

const NAV = [
  { href: "/", label: "Home" },
  { href: "/library", label: "My Library" },
  { href: "/study", label: "Subjects" },
];

export default function Shell({ children }: { children: React.ReactNode }) {
  const { data: user } = useApi<User>("/api/auth/me");
  const pathname = usePathname();
  const router = useRouter();
  if (!user) return null;

  const nav = user.role === "student" ? NAV : [...NAV, { href: "/review", label: "Review" }];
  const isActive = (href: string) => (href === "/" ? pathname === "/" : pathname.startsWith(href));

  async function logout() {
    await post("/api/auth/logout");
    router.replace("/login");
  }

  return (
    <UserContext value={user}>
      <header className="border-b border-line bg-white">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <Link href="/" className="font-display text-lg font-semibold text-brand">
            Study Hub
          </Link>
          <nav className="flex flex-1 flex-wrap gap-1">
            {nav.map((n) => (
              <Link
                key={n.href}
                href={n.href}
                className={`rounded-md px-3 py-1.5 text-sm font-medium ${
                  isActive(n.href) ? "bg-brand/10 text-brand" : "text-muted hover:text-ink"
                }`}
              >
                {n.label}
              </Link>
            ))}
          </nav>
          <div className="flex items-center gap-3 text-sm text-muted">
            <span>
              {user.name} <span className="text-xs">({user.role})</span>
            </span>
            <button onClick={logout} className="font-medium text-brand hover:underline">
              Sign out
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-8">{children}</main>
    </UserContext>
  );
}
