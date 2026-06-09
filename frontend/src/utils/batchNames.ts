type PageInput = {
  puja: string;
  city: string;
  state: string;
};

export function formatBatchName(pageInputs: PageInput[]): string {
  if (pageInputs.length === 0) {
    return "Unnamed batch";
  }

  const first = pageInputs[0];
  const location = first.state ? `${first.city}, ${first.state}` : first.city;
  const label = `${first.puja} · ${location}`;
  const extraPages = pageInputs.length - 1;
  if (extraPages > 0) {
    return `${label} + ${extraPages} more`;
  }
  return label;
}
