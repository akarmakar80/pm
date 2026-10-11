import { Suspense } from "react";
import Shell from "@/components/Shell";

export default function AppLayout({ children }: LayoutProps<"/">) {
  return (
    <Suspense>
      <Shell>{children}</Shell>
    </Suspense>
  );
}
