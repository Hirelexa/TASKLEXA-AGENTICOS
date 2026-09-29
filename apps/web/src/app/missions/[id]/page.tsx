import { MissionDetail } from "@/components/mission/mission-detail";

export default async function MissionPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <MissionDetail missionId={id} />;
}
