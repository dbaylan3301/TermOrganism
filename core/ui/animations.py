from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import dataclass
from typing import Iterable

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

console = Console()


@dataclass(slots=True)
class ThinkingPhase:
    headline: str
    detail: str = ""
    monologue: tuple[str, ...] = ()
    dwell: float = 0.7
    line_delay: float = 0.22


DEFAULT_PHASES: list[ThinkingPhase] = [
    ThinkingPhase(
        "İstek ayrıştırılıyor",
        "ne istendiğini netleştiriyorum",
        (
            "Mesajdaki ana niyeti çıkarıyorum.",
            "Gereksiz yorumdan kaçınıp en olası amacı seçiyorum.",
        ),
    ),
    ThinkingPhase(
        "Bağlam okunuyor",
        "repo ve çalışma durumu inceleniyor",
        (
            "Hangi dizinde olduğumu ve repo tipini kontrol ediyorum.",
            "Gerekirse önceki durum bilgisini hatırlıyorum.",
        ),
    ),
    ThinkingPhase(
        "Plan kuruluyor",
        "en düşük riskli akışı seçiyorum",
        (
            "Önce güvenli ve dar kapsamlı adım düşünüyorum.",
            "Gerekirse bir sonraki adımı şimdiden hazırlıyorum.",
        ),
    ),
    ThinkingPhase(
        "Sonuç hazırlanıyor",
        "ham çıktıyı temiz cevap haline getiriyorum",
        (
            "Log yerine anlaşılır bir özet döneceğim.",
        ),
        dwell=0.9,
    ),
]

PHASE_PRESETS: dict[str, list[ThinkingPhase]] = {
    "repo_status": [
        ThinkingPhase(
            "İstek ayrıştırılıyor",
            "repo durumu sorgusu olarak yorumladım",
            (
                "Branch, değişiklik ve untracked dosyaları toplayacağım.",
            ),
            dwell=0.55,
        ),
        ThinkingPhase(
            "Git okunuyor",
            "durum ve değişiklikler toplanıyor",
            (
                "Ham `git status` çıktısını daha okunur hale getireceğim.",
            ),
            dwell=0.65,
        ),
        ThinkingPhase(
            "Özetleniyor",
            "sonuç insan diline çevriliyor",
            (
                "Sayısal durumla birlikte ilk önemli değişiklikleri göstereceğim.",
            ),
            dwell=0.8,
        ),
    ],
    "repo_summary": [
        ThinkingPhase(
            "İstek ayrıştırılıyor",
            "repo özeti istendiğini anladım",
            (
                "README ve üst seviye yapıyı okuyacağım.",
            ),
            dwell=0.55,
        ),
        ThinkingPhase(
            "Bağlam okunuyor",
            "repo kimliği çıkarılıyor",
            (
                "Repo tipi ve temel giriş noktalarını sezgisel olarak çıkarıyorum.",
                "Gereksiz ayrıntıyı değil ana fikri döndüreceğim.",
            ),
            dwell=0.8,
        ),
        ThinkingPhase(
            "Özet hazırlanıyor",
            "anlaşılır anlatım kuruluyor",
            (
                "Kullanıcıya repo ne yapıyor sorusunun kısa cevabını vereceğim.",
            ),
            dwell=0.85,
        ),
    ],
    "run_tests": [
        ThinkingPhase(
            "Test isteği çözümleniyor",
            "tam suite mi dar koşu mu anlamaya çalışıyorum",
            (
                "Önce ağır olmayan strateji seçmek daha güvenli.",
                "Repo tipine göre test komutunu daraltacağım.",
            ),
            dwell=0.75,
        ),
        ThinkingPhase(
            "Strateji seçiliyor",
            "ilk kırılanı bulan kısa koşu hazırlanıyor",
            (
                "Önce hızlı bilgi veren komutu denemek istiyorum.",
                "Timeout olursa bir sonraki adım daha dar koşu olacak.",
            ),
            dwell=0.85,
        ),
        ThinkingPhase(
            "Test akışı izleniyor",
            "çıktı, fail ve timeout sinyalleri toplanıyor",
            (
                "Ham logu değil karar vermek için gerekli sinyali bekliyorum.",
            ),
            dwell=1.0,
        ),
        ThinkingPhase(
            "Sonuç toparlanıyor",
            "bir sonraki adım da hazırlanıyor",
            (
                "Gerekirse 'daha dar koş' için follow-up akışını açık bırakacağım.",
            ),
            dwell=0.95,
        ),
    ],
    "run_tests_narrow": [
        ThinkingPhase(
            "Follow-up çözümleniyor",
            "önceki test isteğinin daraltılmış hali hazırlanıyor",
            (
                "Bekleyen test akışını daha dar stratejiye çevireceğim.",
            ),
            dwell=0.6,
        ),
        ThinkingPhase(
            "Dar hedef bulunuyor",
            "tek test dosyası veya filtre aranıyor",
            (
                "Repo dışı testleri ve venv içeriğini yok sayıyorum.",
                "En anlamlı dar hedefi seçmeye çalışıyorum.",
            ),
            dwell=0.9,
        ),
        ThinkingPhase(
            "Dar koşu yürütülüyor",
            "daha odaklı sonuç toplanıyor",
            (
                "Burada amacım tüm suite değil, ilk faydalı sinyali almak.",
            ),
            dwell=0.95,
        ),
        ThinkingPhase(
            "Sonuç hazırlanıyor",
            "dar koşunun özeti kuruluyor",
            (
                "Gerekirse bir sonraki teşhis adımını da önereceğim.",
            ),
            dwell=0.8,
        ),
    ],
    "repair": [
        ThinkingPhase(
            "Repair isteği çözümleniyor",
            "hedef dosya ve beklenti netleştiriliyor",
            (
                "Bu bir açıklamalı preview mi yoksa direkt uygulama mı?",
                "Hedef dosyayı ve risk seviyesini çıkarıyorum.",
            ),
            dwell=0.8,
        ),
        ThinkingPhase(
            "Dosya analizi yapılıyor",
            "bağlam ve hata deseni okunuyor",
            (
                "İlgili dosyanın hangi tür arızaya sahip olduğunu anlamaya çalışıyorum.",
            ),
            dwell=0.8,
        ),
        ThinkingPhase(
            "Memory eşleşiyor",
            "synaptic prior ve uygun route aranıyor",
            (
                "Benzer hata daha önce çözüldü mü diye bakıyorum.",
                "Geçmişte güçlü olan route'u öne alacağım.",
            ),
            dwell=0.95,
        ),
        ThinkingPhase(
            "Repair route seçiliyor",
            "en düşük riskli yol hazırlanıyor",
            (
                "Önce deterministic ve güvenli olanı tercih ediyorum.",
            ),
            dwell=0.85,
        ),
        ThinkingPhase(
            "Doğrulama bekleniyor",
            "repair sonrası verify sinyalleri toplanıyor",
            (
                "Sadece patch atmak değil, sonucu da kontrol etmek istiyorum.",
            ),
            dwell=1.0,
        ),
    ],
    "diagnose": [
        ThinkingPhase(
            "Teşhis isteği çözümleniyor",
            "sorunun türü çıkarılıyor",
            (
                "Burada düzeltmeden önce neden-sonuç ilişkisini kuracağım.",
            ),
            dwell=0.7,
        ),
        ThinkingPhase(
            "Bağlam okunuyor",
            "hedef dosya ve hata ilişkisi inceleniyor",
            (
                "En olası sebebi yüksek sesle düşünmeden sadeleştireceğim.",
            ),
            dwell=0.8,
        ),
        ThinkingPhase(
            "Teşhis hazırlanıyor",
            "en olası nedenler sıralanıyor",
            (
                "Önce düşük riskli açıklamayı vereceğim.",
            ),
            dwell=0.85,
        ),
    ],
    "run_project": [
        ThinkingPhase(
            "Çalıştırma isteği çözümleniyor",
            "repo tipi ve amaç ayrıştırılıyor",
            (
                "Bu bir dev server mı, tek script mi, giriş noktası mı ona bakıyorum.",
            ),
            dwell=0.75,
        ),
        ThinkingPhase(
            "Entrypoint aranıyor",
            "uygun komut çıkarılıyor",
            (
                "Repo yapısına göre en olası başlangıç komutunu seçeceğim.",
            ),
            dwell=0.85,
        ),
        ThinkingPhase(
            "Komut hazırlanıyor",
            "çalıştırma akışı kuruluyor",
            (
                "Sonuç gelince ham çıktı yerine kısa yorum döneceğim.",
            ),
            dwell=0.85,
        ),
    ],
    "confirm_pending": [
        ThinkingPhase(
            "Onay çözümleniyor",
            "bekleyen iş tekrar okunuyor",
            (
                "Kullanıcı onay verdi; pending action şimdi uygulanacak.",
            ),
            dwell=0.65,
        ),
        ThinkingPhase(
            "Bekleyen iş uygulanıyor",
            "onaylanan aksiyon yürütülüyor",
            (
                "Session içindeki bekleyen kararı gerçek eyleme çeviriyorum.",
            ),
            dwell=0.95,
        ),
    ],
    "cancel_pending": [
        ThinkingPhase(
            "İptal çözümleniyor",
            "bekleyen iş temizleniyor",
            (
                "Session state'i sadeleştirip akışı kapatacağım.",
            ),
            dwell=0.75,
        ),
    ],
}


def phases_for_goal(goal: str | None) -> list[ThinkingPhase]:
    if not goal:
        return DEFAULT_PHASES
    return PHASE_PRESETS.get(goal, DEFAULT_PHASES)


class TermOrganismAnimator:
    def __init__(self, *, console_: Console | None = None) -> None:
        self.console = console_ or console
        self._stop = asyncio.Event()

    def _panel(
        self,
        phase: ThinkingPhase,
        *,
        title: str = "TermOrganism Thinking",
        reveal_count: int = 0,
        pulse: str = "",
    ) -> Panel:
        items = [
            Text(phase.headline, style="bold yellow"),
            Text(phase.detail, style="grey70"),
        ]

        if phase.monologue:
            items.append(Text(""))
            for line in phase.monologue[:reveal_count]:
                items.append(Text(f"↳ {line}", style="italic grey50"))

        if pulse:
            items.append(Text(""))
            items.append(Text(pulse, style="grey42"))

        return Panel(
            Group(*items),
            title=f"[bold blue]{title}[/bold blue]",
            border_style="blue",
        )

    async def _sleep_or_stop(self, seconds: float) -> bool:
        try:
            await asyncio.wait_for(self._stop.wait(), timeout=seconds)
            return True
        except asyncio.TimeoutError:
            return False

    async def run(
        self,
        *,
        title: str = "TermOrganism Thinking",
        phases: Iterable[ThinkingPhase] | None = None,
        refresh_per_second: float = 12.0,
        transient: bool = True,
    ) -> None:
        sequence = list(phases or DEFAULT_PHASES)
        if not sequence:
            sequence = DEFAULT_PHASES

        with Live(
            self._panel(sequence[0], title=title, reveal_count=0),
            console=self.console,
            refresh_per_second=refresh_per_second,
            transient=transient,
        ) as live:
            for phase in sequence:
                if self._stop.is_set():
                    return

                reveal = 0
                live.update(self._panel(phase, title=title, reveal_count=reveal))

                for _ in phase.monologue:
                    if await self._sleep_or_stop(phase.line_delay):
                        return
                    reveal += 1
                    live.update(self._panel(phase, title=title, reveal_count=reveal))

                if await self._sleep_or_stop(phase.dwell):
                    return

            last = sequence[-1]
            dots = 0
            while not self._stop.is_set():
                pulse = "çalışıyor" + "." * (dots % 4)
                live.update(
                    self._panel(
                        last,
                        title=title,
                        reveal_count=len(last.monologue),
                        pulse=pulse,
                    )
                )
                dots += 1
                if await self._sleep_or_stop(0.35):
                    return

    def stop(self) -> None:
        self._stop.set()


async def run_with_thinking(
    coro,
    *,
    title: str = "TermOrganism Thinking",
    phases: Iterable[ThinkingPhase] | None = None,
):
    animator = TermOrganismAnimator()
    task = asyncio.create_task(animator.run(title=title, phases=phases))
    try:
        return await coro
    finally:
        animator.stop()
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
