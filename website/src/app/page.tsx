import Hero from "@/components/Hero";
import PrivacyCore from "@/components/PrivacyCore";
import BentoGrid from "@/components/BentoGrid";
import ExecutionModes from "@/components/ExecutionModes";
import CodeFlow from "@/components/CodeFlow";
import DownloadSection from "@/components/DownloadSection";

export default function Home() {
  return (
    <>
      <Hero />
      <PrivacyCore />
      <BentoGrid />
      <ExecutionModes />
      <CodeFlow />
      <DownloadSection />
    </>
  );
}
