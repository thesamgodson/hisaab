export default function Loading() {
  return (
    <div className="min-h-screen">
      <nav className="border-b border-gray-100 bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center gap-4">
          <span className="text-lg font-bold text-gray-900">Hisaab</span>
          <div className="flex-1 max-w-md h-10 bg-gray-100 rounded-2xl animate-pulse" />
        </div>
      </nav>

      <main className="max-w-4xl mx-auto px-4 py-8 animate-pulse space-y-6">
        <div className="h-10 w-64 bg-gray-200 rounded-lg" />
        <div className="h-6 w-40 bg-gray-100 rounded-lg" />
        <div className="h-10 w-36 bg-indigo-100 rounded-xl" />
        <div className="grid gap-4 sm:grid-cols-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-48 bg-gray-100 rounded-2xl" />
          ))}
        </div>
      </main>
    </div>
  );
}
