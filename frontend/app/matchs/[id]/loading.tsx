export default function Loading() {
  return (
    <section className="site py-14 md:py-20 animate-pulse">
      <div className="h-6 w-40 bg-grey" />
      <div className="mt-4 h-20 w-full max-w-[720px] bg-grey" />
      <div className="mt-12 h-64 w-full bg-grey/60" />
      <div className="mt-16 grid gap-12 md:grid-cols-2 md:gap-16">
        <div className="h-56 bg-grey/60" />
        <div className="h-56 bg-grey/60" />
      </div>
    </section>
  );
}
