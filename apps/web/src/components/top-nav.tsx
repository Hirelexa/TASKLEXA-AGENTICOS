import Link from "next/link";

export function TopNav() {
  return (
    <nav className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-7xl items-center gap-6 px-5 py-3 lg:px-8">
        <Link href="/" className="text-sm font-semibold tracking-tight text-slate-950">
          Tasklexa Mission Control
        </Link>
        <div className="flex gap-4 text-sm font-medium text-slate-600">
          <Link href="/" className="hover:text-slate-950">
            Dashboard
          </Link>
          <Link href="/agents" className="hover:text-slate-950">
            Agents &amp; Tools
          </Link>
        </div>
      </div>
    </nav>
  );
}
