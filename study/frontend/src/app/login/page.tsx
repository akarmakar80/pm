"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { post } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState("");

  async function submit(form: FormData) {
    try {
      await post("/api/auth/login", { username: form.get("username"), password: form.get("password") });
      router.replace("/");
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <form action={submit} className="w-full max-w-sm space-y-4 rounded-xl border border-line bg-white p-8 shadow-sm">
        <div>
          <h1 className="font-display text-2xl font-semibold text-brand">Study Hub</h1>
          <p className="mt-1 text-sm text-muted">Verified CBSE Class 10 study materials</p>
        </div>
        <label className="block text-sm font-medium">
          Username
          <input name="username" required autoComplete="username"
            className="mt-1 w-full rounded-md border border-line px-3 py-2" />
        </label>
        <label className="block text-sm font-medium">
          Password
          <input name="password" type="password" required autoComplete="current-password"
            className="mt-1 w-full rounded-md border border-line px-3 py-2" />
        </label>
        {error && <p className="text-sm text-warn">{error}</p>}
        <button className="w-full rounded-md bg-brand py-2 font-medium text-white hover:bg-brand-dark">Sign in</button>
      </form>
    </main>
  );
}
