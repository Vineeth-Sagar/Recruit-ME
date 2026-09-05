import { ProfileWizard } from "@/components/profile-wizard/ProfileWizard";

export default function NewProfilePage() {
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight">New job profile</h1>
      <ProfileWizard mode="create" />
    </div>
  );
}
