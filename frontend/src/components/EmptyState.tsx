type Props = {
  emoji: string;
  title: string;
  description: string;
};

export default function EmptyState({ emoji, title, description }: Props) {
  return (
    <div className="empty-state">
      <span className="empty-state__emoji" aria-hidden>
        {emoji}
      </span>
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  );
}
