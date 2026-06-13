/* Capa do YouTube derivada da própria URL — sem upload de imagem no admin.
   A thumbnail oficial é determinística pelo id do vídeo. */

/** Extrai o id de 11 chars de um vídeo do YouTube (watch, youtu.be, embed,
 * shorts, live) ou null se não reconhecer. */
export function youtubeId(url: string | null | undefined): string | null {
  if (!url) return null;
  try {
    const u = new URL(url.trim());
    const host = u.hostname.replace(/^www\./, "");
    if (host === "youtu.be") {
      return u.pathname.slice(1).split("/")[0] || null;
    }
    if (host.endsWith("youtube.com") || host.endsWith("youtube-nocookie.com")) {
      if (u.pathname === "/watch") return u.searchParams.get("v");
      const m = u.pathname.match(/^\/(?:embed|shorts|v|live)\/([^/?#]+)/);
      if (m) return m[1];
    }
  } catch {
    // não é URL completa — talvez o próprio id colado
    if (/^[\w-]{11}$/.test(url.trim())) return url.trim();
  }
  return null;
}

/** Capa oficial (a mesma que o YouTube exibe). hqdefault sempre existe. */
export function youtubeThumb(url: string | null | undefined): string | null {
  const id = youtubeId(url);
  return id ? `https://i.ytimg.com/vi/${id}/hqdefault.jpg` : null;
}

/** URL de watch SEGURA, reconstruída a partir do id extraído — nunca devolve a
 * string crua do banco. Assim um `youtube_url` malicioso (javascript:, data:…)
 * jamais chega a um href: ou vira watch?v=<id> válido, ou null. */
export function youtubeWatchUrl(url: string | null | undefined): string | null {
  const id = youtubeId(url);
  return id ? `https://www.youtube.com/watch?v=${id}` : null;
}
