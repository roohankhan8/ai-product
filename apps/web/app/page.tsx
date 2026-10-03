"use client";
/* eslint-disable react-hooks/set-state-in-effect */

import { useEffect, useState } from "react";
import { api } from "./lib/api";
import { SignIn } from "./components/sign-in";
import { Workspace } from "./components/workspace";

export default function Home() {
  const [token, setToken] = useState<string | null>(null);
  useEffect(() => setToken(window.localStorage.getItem("ai_ops_token")), []);
  if (!token)
    return (
      <SignIn
        onSuccess={(value) => {
          window.localStorage.setItem("ai_ops_token", value);
          setToken(value);
        }}
      />
    );
  return (
    <Workspace
      onSignOut={() => {
        window.localStorage.removeItem("ai_ops_token");
        setToken(null);
      }}
    />
  );
}

export { api };
