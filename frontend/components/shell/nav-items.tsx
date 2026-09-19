import { AutoPayIcon, BillsIcon, CasesIcon, FastagIcon, GiftIcon, HomeIcon, PaymentsIcon, PlaneIcon, RefundsIcon } from "./icons";

export interface NavItem {
  href: string;
  label: string;
  /** Shorter label for the mobile bottom nav's cramped 5-column icon row —
   * falls back to `label` when unset. */
  shortLabel?: string;
  icon: (props: { className?: string }) => JSX.Element;
}

export const PRIMARY_NAV: NavItem[] = [
  { href: "/", label: "Home", icon: HomeIcon },
  { href: "/payments", label: "Payments", icon: PaymentsIcon },
  { href: "/bills", label: "Recharge & Bills", shortLabel: "Bills", icon: BillsIcon },
  { href: "/cases", label: "Cases", icon: CasesIcon },
];

export const MORE_NAV: NavItem[] = [
  { href: "/fastag", label: "FASTag", icon: FastagIcon },
  { href: "/autopay", label: "AutoPay", icon: AutoPayIcon },
  { href: "/refunds", label: "Refunds", icon: RefundsIcon },
  { href: "/travel", label: "Travel", icon: PlaneIcon },
  { href: "/rewards", label: "Rewards", icon: GiftIcon },
];

export const ALL_NAV: NavItem[] = [...PRIMARY_NAV, ...MORE_NAV];
