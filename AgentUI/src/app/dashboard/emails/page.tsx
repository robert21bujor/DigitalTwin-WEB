import EmailReviewDashboard from '@/components/dashboard/EmailReviewDashboard';

export const metadata = {
  title: 'Email Review Queue | Agent Dashboard',
  description: 'Review and approve emails that need manual attention',
  viewport: 'width=device-width, initial-scale=1',
};

export default function EmailsPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <EmailReviewDashboard />
      </div>
    </div>
  );
}