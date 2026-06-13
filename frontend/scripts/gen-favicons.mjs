/* Gera os ícones da marca sem dependências externas (Node puro):
 *   src/app/favicon.ico        16+32+48 (legado + Google/Bing)
 *   src/app/icon.svg           vetor (navegadores modernos)
 *   src/app/apple-icon.png     180×180 opaco (iOS arredonda sozinho)
 *   public/icons/icon-192.png  / icon-512.png (manifest)
 *   public/icons/maskable-512.png (Android adaptive, glifo na zona segura)
 *
 * Desenho: monograma "R" itálico pesado (mesma inclinação do wordmark) em
 * branco sobre o vermelho da marca (#E5372B), cantos arredondados.
 *
 * Uso: node scripts/gen-favicons.mjs
 */

import { deflateSync } from "node:zlib";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const FRONTEND = join(dirname(fileURLToPath(import.meta.url)), "..");

const RED = [0xe5, 0x37, 0x2b];
const WHITE = [0xff, 0xff, 0xff];
const WORLD = 64; // todo o desenho vive num plano 64×64
const RADIUS = 14; // raio dos cantos (proporção ~22%, igual aos cards do site)

// ── Glifo: "R" reto decomposto em retângulos/quadriláteros (sem curvas) ──────
// Caixa 30×36; o shear itálico é aplicado depois (x' = x + SHEAR·(36 − y)).
const SHEAR = 0.22;
const GLYPH_H = 36;
const PARTS = [
  [[0, 0], [9, 0], [9, 36], [0, 36]], // haste
  [[9, 0], [26, 0], [26, 7], [9, 7]], // barra superior
  [[19, 0], [28, 0], [28, 20], [19, 20]], // lateral direita do bojo
  [[9, 13], [28, 13], [28, 20], [9, 20]], // barra do meio
  [[14, 20], [23, 20], [30, 36], [21, 36]], // perna
];

/** Aplica shear, escala e centralização; devolve polígonos no plano 64×64. */
function glyph(scale) {
  const maxX = Math.max(
    ...PARTS.flat().map(([x, y]) => x + SHEAR * (GLYPH_H - y)),
  );
  const w = maxX * scale;
  const h = GLYPH_H * scale;
  const ox = (WORLD - w) / 2;
  const oy = (WORLD - h) / 2;
  return PARTS.map((part) =>
    part.map(([x, y]) => [
      ox + scale * (x + SHEAR * (GLYPH_H - y)),
      oy + scale * y,
    ]),
  );
}

function inPoly(poly, x, y) {
  let inside = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, yi] = poly[i];
    const [xj, yj] = poly[j];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) {
      inside = !inside;
    }
  }
  return inside;
}

function inRoundedRect(x, y, r) {
  if (x < 0 || x > WORLD || y < 0 || y > WORLD) return false;
  const dx = Math.max(Math.abs(x - WORLD / 2) - (WORLD / 2 - r), 0);
  const dy = Math.max(Math.abs(y - WORLD / 2) - (WORLD / 2 - r), 0);
  return dx * dx + dy * dy <= r * r;
}

/** Rasteriza com supersampling; devolve RGBA (px×px×4). */
function render(px, { scale = 1.15, opaque = false } = {}) {
  const ss = px >= 192 ? 2 : 4;
  const polys = glyph(scale);
  const out = new Uint8Array(px * px * 4);
  const unit = WORLD / px;
  for (let j = 0; j < px; j++) {
    for (let i = 0; i < px; i++) {
      let r = 0;
      let g = 0;
      let b = 0;
      let hits = 0;
      for (let sy = 0; sy < ss; sy++) {
        for (let sx = 0; sx < ss; sx++) {
          const wx = (i + (sx + 0.5) / ss) * unit;
          const wy = (j + (sy + 0.5) / ss) * unit;
          if (!opaque && !inRoundedRect(wx, wy, RADIUS)) continue;
          const cor = polys.some((p) => inPoly(p, wx, wy)) ? WHITE : RED;
          r += cor[0];
          g += cor[1];
          b += cor[2];
          hits++;
        }
      }
      const o = (j * px + i) * 4;
      if (hits > 0) {
        out[o] = Math.round(r / hits);
        out[o + 1] = Math.round(g / hits);
        out[o + 2] = Math.round(b / hits);
        out[o + 3] = Math.round((hits / (ss * ss)) * 255);
      }
    }
  }
  return out;
}

// ── PNG (zlib + CRC32, espec. mínima) ────────────────────────────────────────
const CRC_TABLE = new Uint32Array(256).map((_, n) => {
  let c = n;
  for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
  return c >>> 0;
});

function crc32(buf) {
  let c = 0xffffffff;
  for (const byte of buf) c = CRC_TABLE[(c ^ byte) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

function chunk(tipo, dados) {
  const len = Buffer.alloc(4);
  len.writeUInt32BE(dados.length);
  const corpo = Buffer.concat([Buffer.from(tipo, "ascii"), dados]);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(corpo));
  return Buffer.concat([len, corpo, crc]);
}

function pngEncode(px, rgba) {
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(px, 0);
  ihdr.writeUInt32BE(px, 4);
  ihdr[8] = 8; // 8 bits/canal
  ihdr[9] = 6; // RGBA
  const stride = px * 4;
  const raw = Buffer.alloc(px * (stride + 1));
  for (let y = 0; y < px; y++) {
    raw.set(rgba.subarray(y * stride, (y + 1) * stride), y * (stride + 1) + 1);
  }
  return Buffer.concat([
    Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]),
    chunk("IHDR", ihdr),
    chunk("IDAT", deflateSync(raw, { level: 9 })),
    chunk("IEND", Buffer.alloc(0)),
  ]);
}

// ── ICO (DIBs BMP 32bpp — máxima compatibilidade em tamanhos pequenos) ──────
function bmpDib(px, rgba) {
  const header = Buffer.alloc(40);
  header.writeUInt32LE(40, 0);
  header.writeInt32LE(px, 4);
  header.writeInt32LE(px * 2, 8); // altura dobrada: XOR + máscara AND
  header.writeUInt16LE(1, 12);
  header.writeUInt16LE(32, 14);
  const xor = Buffer.alloc(px * px * 4);
  for (let y = 0; y < px; y++) {
    const src = (px - 1 - y) * px * 4; // BMP é bottom-up
    for (let x = 0; x < px; x++) {
      const s = src + x * 4;
      const d = (y * px + x) * 4;
      xor[d] = rgba[s + 2]; // B
      xor[d + 1] = rgba[s + 1]; // G
      xor[d + 2] = rgba[s]; // R
      xor[d + 3] = rgba[s + 3]; // A
    }
  }
  const and = Buffer.alloc(Math.ceil(px / 32) * 4 * px); // alpha já resolve
  return Buffer.concat([header, xor, and]);
}

function icoEncode(tamanhos) {
  const dibs = tamanhos.map((px) => ({ px, dib: bmpDib(px, render(px)) }));
  const header = Buffer.alloc(6);
  header.writeUInt16LE(1, 2); // tipo: ícone
  header.writeUInt16LE(dibs.length, 4);
  let offset = 6 + 16 * dibs.length;
  const dirs = [];
  for (const { px, dib } of dibs) {
    const d = Buffer.alloc(16);
    d[0] = px >= 256 ? 0 : px;
    d[1] = d[0];
    d.writeUInt16LE(1, 4);
    d.writeUInt16LE(32, 6);
    d.writeUInt32LE(dib.length, 8);
    d.writeUInt32LE(offset, 12);
    dirs.push(d);
    offset += dib.length;
  }
  return Buffer.concat([header, ...dirs, ...dibs.map((x) => x.dib)]);
}

// ── SVG (mesmo desenho, vetorial) ────────────────────────────────────────────
function svg() {
  const d = glyph(1.15)
    .map(
      (p) =>
        `M${p.map(([x, y]) => `${x.toFixed(2)} ${y.toFixed(2)}`).join("L")}Z`,
    )
    .join("");
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${WORLD} ${WORLD}">` +
    `<rect width="${WORLD}" height="${WORLD}" rx="${RADIUS}" fill="#E5372B"/>` +
    `<path d="${d}" fill="#fff"/></svg>\n`
  );
}

// ── Saídas ───────────────────────────────────────────────────────────────────
const ICONS_DIR = join(FRONTEND, "public", "icons");
mkdirSync(ICONS_DIR, { recursive: true });

writeFileSync(join(FRONTEND, "src", "app", "favicon.ico"), icoEncode([16, 32, 48]));
writeFileSync(join(FRONTEND, "src", "app", "icon.svg"), svg());
writeFileSync(
  join(FRONTEND, "src", "app", "apple-icon.png"),
  pngEncode(180, render(180, { opaque: true })),
);
writeFileSync(join(ICONS_DIR, "icon-192.png"), pngEncode(192, render(192)));
writeFileSync(join(ICONS_DIR, "icon-512.png"), pngEncode(512, render(512)));
writeFileSync(
  join(ICONS_DIR, "maskable-512.png"),
  pngEncode(512, render(512, { opaque: true, scale: 0.82 })),
);

console.log("Ícones gerados: favicon.ico, icon.svg, apple-icon.png, icons/*.png");
