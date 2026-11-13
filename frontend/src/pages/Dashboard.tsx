import AdminStatsCards from '@/components/AdminStatsCards';
import { ROLE_LABEL } from '@/components/AppLayout';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useMe } from '@/hooks/useAuth';

export default function Dashboard() {
  const { data: user } = useMe();

  // ProtectedRoute only renders this once the user has loaded.
  if (!user) return null;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>

      {user.role === 'admin' && <AdminStatsCards />}

      <Card className="max-w-md">
        <CardHeader>
          <CardTitle>Your account</CardTitle>
          <CardDescription>Prototype — all data is synthetic.</CardDescription>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-3 text-sm">
            <dt className="text-muted-foreground">Signed in as</dt>
            <dd className="font-medium">{user.email}</dd>
            <dt className="text-muted-foreground">Role</dt>
            <dd>
              <Badge variant="secondary">{ROLE_LABEL[user.role]}</Badge>
            </dd>
            {user.institution && (
              <>
                <dt className="text-muted-foreground">Institution</dt>
                <dd>
                  {user.institution.name} ({user.institution.code})
                </dd>
              </>
            )}
          </dl>
        </CardContent>
      </Card>
    </div>
  );
}
