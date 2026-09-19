import { BusIcon, PlaneIcon, TrainIcon } from "@/components/shell/icons";

const TRIPS = [
  { title: "Flights", desc: "Domestic & international fares, tracked in one place.", icon: PlaneIcon },
  { title: "Trains", desc: "IRCTC bookings with live PNR status.", icon: TrainIcon },
  { title: "Bus", desc: "Intercity bus tickets from 500+ operators.", icon: BusIcon },
];

export default function TravelPage() {
  return (
    <div className="page-shell space-y-5">
      <div>
        <h1 className="text-xl font-bold text-ink">Travel</h1>
        <p className="text-sm text-ink-secondary mt-1">Book and manage your trips.</p>
      </div>
      <div className="grid sm:grid-cols-3 gap-4 stagger-list">
        {TRIPS.map((t) => {
          const Icon = t.icon;
          return (
            <div
              key={t.title}
              className="stagger-item card card-hover p-5 transition-all duration-200 hover:-translate-y-0.5"
            >
              <span className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-light text-brand-dark mb-3">
                <Icon className="w-5 h-5" />
              </span>
              <div className="text-sm font-semibold text-ink">{t.title}</div>
              <p className="text-xs text-ink-secondary mt-1">{t.desc}</p>
            </div>
          );
        })}
      </div>
      <div className="card p-5 text-sm text-ink-secondary">
        No upcoming trips. If a booking payment ever fails, Nishchint will monitor and resolve it the same way it
        handles any other payment exception.
      </div>
    </div>
  );
}
