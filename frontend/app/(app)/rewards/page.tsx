import { GiftIcon } from "@/components/shell/icons";

const OFFERS = [
  { title: "5% cashback on electricity bills", tag: "Bills" },
  { title: "₹50 off your next FASTag recharge", tag: "FASTag" },
  { title: "Zero-fee AutoPay setup this month", tag: "AutoPay" },
  { title: "2x rewards on UPI payments above ₹500", tag: "UPI" },
];

export default function RewardsPage() {
  return (
    <div className="page-shell space-y-5">
      <div>
        <h1 className="text-xl font-bold text-ink">Rewards</h1>
        <p className="text-sm text-ink-secondary mt-1">Offers picked for you based on your activity.</p>
      </div>
      <div className="grid sm:grid-cols-2 gap-4 stagger-list">
        {OFFERS.map((o) => (
          <div
            key={o.title}
            className="stagger-item card card-hover p-5 transition-all duration-200 hover:-translate-y-0.5 flex items-start gap-3"
          >
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-brand-light text-brand-dark">
              <GiftIcon className="w-5 h-5" />
            </span>
            <div>
              <span className="badge bg-brand-light text-brand-dark">{o.tag}</span>
              <div className="text-sm font-medium text-ink mt-2">{o.title}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
