import Link from "next/link";
import SearchBar from "@/components/SearchBar";

export default function Home() {
  return (
    <main className="flex-1 flex flex-col items-center justify-center px-4 py-16">
      <div className="text-center mb-10">
        <h1 className="text-5xl font-bold tracking-tight text-gray-900 mb-2">
          <span className="block text-3xl text-gray-400 mb-1">
            &#x0939;&#x093F;&#x0938;&#x093E;&#x092C;
          </span>
          Hisaab
        </h1>
        <p className="text-lg text-gray-500 mt-4">Where did the money go?</p>
        <p className="text-sm text-gray-400 mt-1">
          8 government schemes. Every district. Verified data.
        </p>
      </div>

      <SearchBar autoFocus />

      <div className="mt-16 grid grid-cols-2 sm:grid-cols-4 gap-3 max-w-2xl w-full">
        {[
          { name: "MGNREGA", desc: "Employment" },
          { name: "PMGSY", desc: "Rural Roads" },
          { name: "PMAY-G", desc: "Housing" },
          { name: "PM Kisan", desc: "Farmer Income" },
          { name: "JJM", desc: "Tap Water" },
          { name: "PM POSHAN", desc: "School Meals" },
          { name: "NSAP", desc: "Pensions" },
          { name: "PDS/NFSA", desc: "Rations" },
        ].map((s) => (
          <div
            key={s.name}
            className="text-center px-3 py-3 rounded-xl bg-white border border-gray-100 shadow-sm"
          >
            <p className="text-sm font-medium text-gray-800">{s.name}</p>
            <p className="text-xs text-gray-400">{s.desc}</p>
          </div>
        ))}
      </div>

      <footer className="mt-16 text-center text-xs text-gray-400 space-y-1">
        <p>
          Data sourced from official government portals.{" "}
          <Link href="/about" className="underline hover:text-gray-600">
            How it works
          </Link>
        </p>
        <p>
          Hisaab is open-source public infrastructure. Not affiliated with any
          government body.
        </p>
      </footer>
    </main>
  );
}
