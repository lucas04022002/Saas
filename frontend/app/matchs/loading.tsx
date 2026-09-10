export default function Loading() {
  return <section className="site py-20 animate-pulse"><div className="h-12 w-64 bg-grey" />{[0, 1, 2, 3].map((i) => <div key={i} className="mt-6 h-16 border-t border-line bg-grey/60" />)}</section>;
}
