export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/40 px-4 py-12">
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <div className="text-lg font-semibold tracking-tight">Recruit-ME</div>
          <p className="text-sm text-muted-foreground">Job-search automation</p>
        </div>
        {children}
      </div>
    </div>
  );
}
