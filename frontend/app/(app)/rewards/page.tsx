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
      <div className="grid sm:grid-cols-2 gap-4">
        {OFFERS.map((o) => (
          <div key={o.title} className="card p-5">
            <span className="badge bg-brand-light text-brand-dark">{o.tag}</span>
            <div className="text-sm font-medium text-ink mt-2">{o.title}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
