export function MarkdownContent({ content }: { content: string }) {
  const blocks: React.ReactNode[] = [];
  let list: { ordered: boolean; items: string[] } | null = null;
  const inline = (text: string) =>
    text
      .split(/(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^\)]+\))/g)
      .map((token, index) => {
        if (token.startsWith("**"))
          return <strong key={index}>{token.slice(2, -2)}</strong>;
        if (token.startsWith("`"))
          return <code key={index}>{token.slice(1, -1)}</code>;
        const link = token.match(/^\[([^\]]+)\]\(([^\)]+)\)$/);
        return link ? (
          <a key={index} href={link[2]} target="_blank" rel="noreferrer">
            {link[1]}
          </a>
        ) : (
          <span key={index}>{token}</span>
        );
      });
  const flush = () => {
    if (!list) return;
    const Tag = list.ordered ? "ol" : "ul";
    blocks.push(
      <Tag className="mb-4 list-inside space-y-1 pl-2" key={blocks.length}>
        {list.items.map((item, index) => (
          <li key={index}>{inline(item)}</li>
        ))}
      </Tag>,
    );
    list = null;
  };
  content.split("\n").forEach((line, index) => {
    const heading = line.match(/^(#{1,4})\s+(.+)$/);
    const bullet = line.match(/^\s*[-*]\s+(.+)$/);
    const ordered = line.match(/^\s*\d+[.)]\s+(.+)$/);
    if (heading) {
      flush();
      const Tag = `h${heading[1].length}` as keyof React.JSX.IntrinsicElements;
      blocks.push(
        <Tag
          className="mb-2 mt-5 text-lg font-bold tracking-tight first:mt-0"
          key={index}
        >
          {inline(heading[2])}
        </Tag>,
      );
    } else if (bullet || ordered) {
      const isOrdered = Boolean(ordered);
      if (!list || list.ordered !== isOrdered) {
        flush();
        list = { ordered: isOrdered, items: [] };
      }
      list.items.push((bullet || ordered)![1]);
    } else if (!line.trim()) flush();
    else {
      flush();
      blocks.push(
        <p className="mb-3 last:mb-0" key={index}>
          {inline(line)}
        </p>,
      );
    }
  });
  flush();
  return <div className="leading-7">{blocks}</div>;
}
