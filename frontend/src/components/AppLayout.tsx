import { LogOut } from 'lucide-react';
import { NavLink, Outlet } from 'react-router-dom';

import type { components } from '@/api/schema';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useLogout, useMe } from '@/hooks/useAuth';
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
}

const NAV: NavItem[] = [
  { to: '/', label: 'Dashboard' },
  { to: '/certificates', label: 'Certificates', roles: ['institution', 'admin'] },
  { to: '/certificates/import', label: 'Import CSV', roles: ['institution'] },
  { to: '/verify', label: 'Verify', roles: ['verifier', 'admin'] },
  { to: '/verifications', label: 'History', roles: ['verifier', 'admin'] },
];

/** Page chrome for logged-in pages. Rendered inside ProtectedRoute. */
export default function AppLayout() {
  const { data: user } = useMe();
  const logout = useLogout();

  if (!user) return null;

  const items = NAV.filter((item) => !item.roles || item.roles.includes(user.role));

  return (
    <div className="min-h-screen bg-muted/40">
      <header className="border-b bg-background print:hidden">
        <div className="mx-auto flex max-w-5xl items-center gap-6 px-4 py-3">
          <span className="font-semibold">Authenticity Validator</span>
          <nav className="flex flex-1 gap-1 overflow-x-auto">
            {items.map((item) => (
              <NavLink
                key={item.to}
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
