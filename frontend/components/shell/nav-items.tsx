import { AutoPayIcon, BillsIcon, CasesIcon, FastagIcon, HomeIcon, PaymentsIcon, RefundsIcon } from "./icons";

export interface NavItem {
  href: string;
  label: string;
  icon: (props: { className?: string }) => JSX.Element;
}

export const PRIMARY_NAV: NavItem[] = [
  { href: "/", label: "Home", icon: HomeIcon },
  { href: "/payments", label: "Payments", icon: PaymentsIcon },
  { href: "/bills", label: "Bills", icon: BillsIcon },
  { href: "/cases", label: "Cases", icon: CasesIcon },
];

export const MORE_NAV: NavItem[] = [
  { href: "/fastag", label: "FASTag", icon: FastagIcon },
  { href: "/autopay", label: "AutoPay", icon: AutoPayIcon },
  { href: "/refunds", label: "Refunds", icon: RefundsIcon },
  { href: "/travel", label: "Travel", icon: PaymentsIcon },
  { href: "/rewards", label: "Rewards", icon: PaymentsIcon },
];

export const ALL_NAV: NavItem[] = [...PRIMARY_NAV, ...MORE_NAV];
