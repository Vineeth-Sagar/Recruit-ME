"use client";

import { ProfileWizard } from "@/components/profile-wizard/ProfileWizard";

export default function EditProfilePage({ params }: { params: { id: string } }) {
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight">Edit job profile</h1>
      <ProfileWizard mode="edit" profileId={params.id} />
    </div>
  );
}
