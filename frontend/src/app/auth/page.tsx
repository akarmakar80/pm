"use client";

import { FormEvent, useEffect, useState } from "react";
import { KanbanBoard } from "@/components/KanbanBoard";

const STORAGE_KEY = "pm_logged_in";

export default function AuthPage() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    setIsAuthenticated(localStorage.getItem(STORAGE_KEY) === "true");
    setIsReady(true);
  }, []);

  const setLoggedIn = (state: boolean) => {
    if (state) {
      localStorage.setItem(STORAGE_KEY, "true");
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
    setIsAuthenticated(state);
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (username.trim() === "user" && password === "password") {
      setLoggedIn(true);
      setError("");
      return;
    }
    setError("Invalid credentials. Use user/password.");
  };

  const handleLogout = () => {
    setLoggedIn(false);
  };

  if (!isReady) {
    return null;
  }

  if (isAuthenticated) {
    return <KanbanBoard user={username} onLogout={handleLogout} />;
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-8 shadow-lg"
      >
        <h1 className="mb-4 text-2xl font-bold text-slate-900">Please sign in</h1>
        <label className="mb-2 block text-sm font-medium text-slate-700">
          Username
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
            placeholder="user"
          />
        </label>
        <label className="mb-4 block text-sm font-medium text-slate-700">
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
            placeholder="password"
          />
        </label>
        <button
          type="submit"
          className="w-full rounded-md bg-blue-600 px-3 py-2 text-white hover:bg-blue-700"
        >
          Sign in
        </button>
        {error ? <p className="mt-3 text-xs text-red-600">{error}</p> : null}
      </form>
    </main>
  );
}
