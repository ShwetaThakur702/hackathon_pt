const TRIPS = [
  { title: "Flights", desc: "Domestic & international fares, tracked in one place." },
  { title: "Trains", desc: "IRCTC bookings with live PNR status." },
  { title: "Bus", desc: "Intercity bus tickets from 500+ operators." },
];

export default function TravelPage() {
  return (
    <div className="page-shell space-y-5">
      <div>
        <h1 className="text-xl font-bold text-ink">Travel</h1>
        <p className="text-sm text-ink-secondary mt-1">Book and manage your trips.</p>
      </div>
      <div className="grid sm:grid-cols-3 gap-4">
        {TRIPS.map((t) => (
          <div key={t.title} className="card p-5">
            <div className="text-sm font-semibold text-ink">{t.title}</div>
            <p className="text-xs text-ink-secondary mt-1">{t.desc}</p>
          </div>
        ))}
      </div>
      <div className="card p-5 text-sm text-ink-secondary">
        No upcoming trips. If a booking payment ever fails, Nishchint will monitor and resolve it the same way it
        handles any other payment exception.
      </div>
    </div>
  );
}
