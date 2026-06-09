type Props = {
  message?: string;
};

export default function LoadingState({ message = "Loading…" }: Props) {
  return (
    <div className="loading-block" role="status">
      <span className="spinner" aria-hidden />
      {message}
    </div>
  );
}
