import { LogOut } from 'lucide-react';
import { NavLink, Outlet } from 'react-router-dom';

import type { components } from '@/api/schema';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useLogout, useMe } from '@/hooks/useAuth';
import { useReviewCounts } from '@/hooks/useReviews';
import { cn } from '@/lib/utils';

type Role = components['schemas']['Role'];

export const ROLE_LABEL: Record<Role, string> = {
  admin: 'Administrator',
  institution: 'Institution',
  verifier: 'Verifier',
};

interface NavItem {
  to: string;
  label: string;
  roles?: Role[];
  /** Show the open-request count beside the label. */
  badge?: 'requests';
}

const NAV: NavItem[] = [
  { to: '/', label: 'Dashboard' },
  { to: '/certificates', label: 'Certificates', roles: ['institution', 'admin'] },
  { to: '/certificates/import', label: 'Import CSV', roles: ['institution'] },
  { to: '/verify', label: 'Verify', roles: ['verifier', 'admin'] },
  { to: '/verifications', label: 'History', roles: ['verifier', 'admin'] },
  // Same route for everyone, labelled for who is reading it: work to do for
  // an institution, answers awaited for a verifier.
  { to: '/requests', label: 'Requests', roles: ['verifier'], badge: 'requests' },
  { to: '/requests', label: 'Verification requests', roles: ['institution'], badge: 'requests' },
  { to: '/requests', label: 'Requests', roles: ['admin'], badge: 'requests' },
  { to: '/admin/institutions', label: 'Institutions', roles: ['admin'] },
  { to: '/admin/audit', label: 'Audit log', roles: ['admin'] },
];

/** Page chrome for logged-in pages. Rendered inside ProtectedRoute. */
export default function AppLayout() {
  const { data: user } = useMe();
  const logout = useLogout();
  // Scoped server-side, so one query serves every role.
  const counts = useReviewCounts(Boolean(user));

  if (!user) return null;

  const items = NAV.filter((item) => !item.roles || item.roles.includes(user.role));
  const openRequests = counts.data?.open ?? 0;

  return (
    <div className="min-h-screen bg-muted/40">
      <header className="border-b bg-background print:hidden">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <span className="font-semibold">Authenticity Validator</span>
          {/* Wraps to a second row rather than scrolling: an admin has five
              items and they must all stay clickable on a laptop. */}
          <nav className="order-last flex w-full flex-wrap gap-1 sm:order-none sm:w-auto sm:flex-1">
            {items.map((item) => (
              <NavLink
                key={`${item.to}-${item.label}`}
                to={item.to}
                end
                className={({ isActive }) =>
                  cn(
                    'whitespace-nowrap rounded-md px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground',
                    isActive && 'bg-muted font-medium text-foreground',
                  )
                }
              >
                {item.label}
                {item.badge === 'requests' && openRequests > 0 && (
                  <span
                    className="ml-1.5 rounded-full bg-primary px-1.5 py-0.5 text-xs font-medium text-primary-foreground"
                    aria-label={`${openRequests} open`}
                  >
                    {openRequests}
                  </span>
                )}
              </NavLink>
            ))}
          </nav>
          <div className="flex items-center gap-3">
            <span className="hidden text-sm text-muted-foreground sm:inline">{user.email}</span>
            <Badge variant="secondary">{ROLE_LABEL[user.role]}</Badge>
            <Button variant="outline" size="sm" onClick={logout}>
              <LogOut />
              Log out
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  );
}
