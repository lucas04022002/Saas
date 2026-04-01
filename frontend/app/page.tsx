import FAQ from "../components/sections/faq/default";
import Footer from "../components/sections/footer/default";
import Hero from "../components/sections/hero/default";
import Items from "../components/sections/items/default";
import Navbar from "../components/sections/navbar/default";
import Opportunities from "../components/sections/opportunities/default";
import Pricing from "../components/sections/pricing/default";
import Stats from "../components/sections/stats/default";

export default function Home() {
  return (
    <main className="bg-[#10131a] text-white min-h-screen w-full">
      <Navbar />
      <Hero />
      <Stats />
      <Opportunities />
      <Items />
      <Pricing />
      <FAQ />
      <Footer />
    </main>
  );
}
