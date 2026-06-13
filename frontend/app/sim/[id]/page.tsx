import { sampleResult } from "../../../lib/sampleResult";
import { SimClient } from "./SimClient";

// `output: 'export'` pre-renders dynamic routes from generateStaticParams only.
// The hosted build is demo-only, so the single statically-emitted route is the
// bundled sample result; live sims (random sim_ids) are served by the local dev
// server, where dynamicParams is not enforced.
export const dynamicParams = false;

export function generateStaticParams() {
  return [{ id: sampleResult.sim_id }];
}

export default async function SimPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <SimClient id={id} />;
}
