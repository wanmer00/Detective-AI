# Detective AI — речь по 12 слайдам (5 минут)

**Спикер 1 — Elchin Abdullaev:** история, пользователи, бизнес, финал.
**Спикер 2 — Rihat Orucov:** решение, технология, отличия, демо, планы.
Ремарки в [скобках] — для вас, их не произносить.

---

### Слайд 1 · Обложка · ELCHIN · 0:00–0:08
«Salam. Biz Opium Team-ik, layihəmiz — Detective AI. Texnologiyadan yox, burada, Bakıda baş vermiş bir hekayədən başlayaq.»

### Слайд 2 · Sİ və deepfake təhdidi Azərbaycanda · ELCHIN · 0:08–0:35
[Медленно, смотреть на жюри, не на экран.]
«Bu ilin fevralında BDU-nun hüquq fakültəsinin və digər universitetlərin tələbə qızları mesajlar aldılar. Onların fotolarını TikTok-dan götürüb süni intellektlə dəyişdirdilər, təhqiredici yazılar əlavə etdilər və saxta hesablardan yaydılar. Sonra isə mesaj gəldi: pul ver — silim.»
[ПАУЗА 2 секунды.]
«Kiberpolis cinayətkarı tapdı. Amma o ilk axşam həmin qızın yerində özünüzü təsəvvür edin. Valideynləri, qrup yoldaşları, müəllimləri artıq fotonu görüb. O, bunun saxta olduğunu necə sübut etsin?»

### Слайд 3 · Miqyas · ELCHIN · 0:35–0:45
«Və bu, tək hadisə deyil. Deepfake insidentlərinin 84 faizinin hədəfi qadınlardır. Saxta foto yaratmaq — bir dəqiqədir. Amma onun saxta olduğunu sübut etmək üçün qurbanın sadəcə aləti yoxdur. Rihat nə etdiyimizi göstərəcək.»

### Слайд 4 · Həll: dörd addım · RIHAT · 0:45–1:05
«Detective AI — təsvirin rəqəmsal ekspertizasıdır. Dörd addım: fotonu yükləyirsiniz — hətta WhatsApp-dan gələni. Sistem beş müstəqil yoxlama aparır. Sonra şəffaf hökm verir — lehinə və əleyhinə sübutlarla. Və sonda polisə təqdim etmək üçün PDF hesabat. Hər şey lokal işləyir: qurbanın fotosu buluda getmir.»

### Слайд 5 · Arxitektura · RIHAT · 1:05–1:15
«Daxildə — bir analiz mühərriki: iki müstəqil Sİ detektoru, metaməlumat və C2PA imzaları, vaxt xətti, sıxılma analizi və üz analizi. Ballar ortalanmır — hökmü şəffaf qaydalar verir. Hamısı açıq lisenziyalı modellərdir.»

### Слайд 6 · Fərqimiz · RIHAT · 1:15–1:35
«Adi onlayn detektor bir faiz verir və həmişə cavab verir. Biz isə iki müstəqil detektordan istifadə edirik və onlar razılaşmasa, bunu göstəririk. Sübut azdırsa, «həqiqi fotodur» demirik — şantaj qurbanı üçün yalançı «həqiqi» ən pis səhvdir. Testlərimizdə sistemin səhvən «həqiqi» adlandırdığı sıxılmış Sİ fotoları 16 idi — indi sıfırdır. Gəlin canlı göstərim.»

### Слайд 7 · Canlı demo · RIHAT · 1:35–3:15
[Слайд показать 3 секунды → переключиться на приложение. Интерфейс на AZ.]
1. «Bu, WhatsApp ilə gələn fotodur.» [загрузить заранее проверенное ИИ-фото]
2. «Görürsünüz — sistem sadəcə «Sİ» demir. Burada hər detektorun rəyi, aşkarlama inamı və bu nəticəyə gətirən qayda var.» [прокрутить к хронологии] «Burada isə faylın vaxt xətti və metaməlumatları.»
3. [открыть PDF] «Bu hesabatı çap edib polisə ərizəyə əlavə etmək olar: SHA-256 heşi məhz bu faylın yoxlandığını təsdiqləyir.»
4. [если есть 10 секунд] «Bu isə bu səhər telefonla çəkdiyim fotodur — kamera məlumatları var, nəticə: ehtimal ki, həqiqi.»
[ПЛАН Б: если зависло — вернуться на этот слайд] «Vaxtınızı almamaq üçün səhər aldığımız real nəticəni göstərirəm: burada detektorlar razılaşmır və şəkil çox kiçikdir — ona görə sistem dürüstcə «qəti nəticə yoxdur» deyir.»

### Слайд 8 · Kim istifadə edəcək · ELCHIN · 3:15–3:40
«Bundan kim istifadə edəcək? Birincisi — qurbanlar, onlar üçün pulsuz. İkincisi — kiberpolis: onlara internetsiz, öz serverlərində işləyən sürətli ilkin ekspertiza lazımdır. Üçüncüsü — universitetlər: BDU hadisəsi göstərdi ki, onların reaksiya alətinə ehtiyacı var. Dördüncüsü — banklar və sığorta: onlara gələn selfi və zərər fotolarını artıq neyron şəbəkə ilə saxtalaşdırmaq olur.»

### Слайд 9 · Biznes modeli: B2B SaaS + hər skana ödəniş · ELCHIN · 3:40–4:10
«Biznes modelimiz — B2B SaaS və hər skana ödəniş. Pulsuz planda ayda 10 skan var. Pro — ayda 19 dollara 500 skan, tarixçə və PDF hesabatlar. Business — 99 dollara 5 000 skan və API. Enterprise — 499 dollardan: fərdi inteqrasiya və SLA. Gəlir abunələrdən, əlavə skan kreditlərindən, enterprise lisenziyalardan və API inteqrasiyalarından gəlir. Bunlar təklif etdiyimiz qiymətlərdir.»

### Слайд 10 · Bazar strategiyası · ELCHIN · 4:10–4:40
«Azərbaycanda başlayırıq. İlk müştərilərimiz — marketpleyslər, media, sığorta şirkətləri və marketinq agentlikləridir: onların hamısı hər gün saxta ola biləcək fotolarla işləyir. Tələbi B2B tərəfdaşlıqla təsdiqləyib, API ilə beynəlxalq bazara çıxırıq. Nümunə ssenari: 100 Pro, 20 Business və 2 Enterprise müştəri — ayda təxminən 4 900, ildə 58 min dollardan çox. Üstünlüyümüz — bir neçə ekspertiza siqnalı, şəffaf analiz, hesabat və API bir platformada. Rihat, bəs sonra?»
[Цифры назвать как пример, не как факт: «nümunə ssenari».]

### Слайд 11 · Növbəti addımlar · RIHAT · 4:40–4:55
«Sonra — kiberpolis və universitetlərlə pilot, WhatsApp və Telegram botu ki, fotonu bir kliklə yoxlamaq olsun, video və səs deepfake-lərinin yoxlanması və regionumuzdan öz böyük məlumat dəstimiz.»

### Слайд 12 · Финал · ELCHIN · 4:55–5:00
[Медленно, оба смотрят на жюри.]
«Fotonu saxtalaşdırmaq — bir dəqiqədir. İndi saxtalığı sübut etmək də.»
[Пауза.]
«Təşəkkür edirik! Suallarınızı məmnuniyyətlə cavablandırarıq.»

---

## Вопросы жюри (2 минуты)
Технику отвечает Rihat, бизнес — Elchin. Ответ — 15–20 секунд.

- **Dəqiqliyiniz nə qədərdir?** — «Dürüst deyək: kiçik test dəstində yoxlamışıq — 19 Sİ və 35 real foto, üstəlik onların sıxılmış nüsxələri. Orijinallarda F1 0,86-dır. Əsas nəticə: sıxılmış Sİ fotolarını «həqiqi» adlandırma səhvi 16-dan 0-a düşdü. Növbəti addım — böyük məlumat dəsti.»
- **Hive, Sensity kimi xidmətlərdən fərqiniz?** — «Onlar buludda işləyir və bir faiz verir. Biz oflayn işləyirik, foto heç yerə getmir, nəticəni sübutlarla izah edirik və Azərbaycan dilində polis üçün hesabat veririk.»
- **Detektoru aldatmaq olar?** — «Bəli, heç bir detektor 100% deyil, bunu hesabatda açıq yazırıq. Ona görə bir yox, bir neçə müstəqil yoxlama edirik və əmin olmayanda «qəti deyil» deyirik.»
- **«Qəti deyil» çox çıxırsa, faydası nədir?** — «Qurban üçün ən təhlükəlisi yalançı «həqiqi»dir. «Qəti deyil» insanı orijinal faylı tapmağa və polisə müraciət etməyə yönəldir.»
- **BDU fotosunu tapardınız?** — «O fotolar bizdə yoxdur, vəd vermirik. Sistem Sİ generasiyasını, metaməlumatı və redaktə izlərini yoxlayır; üzərinə yazı əlavə edilmiş montajlar hələ zəif yerimizdir və planımızdadır.»
- **Kim ödəyəcək?** — «Şirkətlər: marketpleyslər, media, sığorta və marketinq agentlikləri — Pro, Business və Enterprise planları ilə. Fərdi istifadəçi və qurbanlar üçün pulsuz plan qalır.»
- **Bu gəlir rəqəmləri realdır?** — «Xeyr, bu nümunə ssenaridir. Hələ ödənişli müştərimiz yoxdur; qiymətləri ilk B2B tərəfdaşlarla yoxlayacağıq.»
- **Niyə marketpleys sizə pul ödəsin?** — «Saxta məhsul şəkilləri, saxta rəylər və saxta zərər fotoları onlara birbaşa pul itkisidir. API ilə hər şəkil yüklənəndə avtomatik yoxlanır.»
- **Məlumat təhlükəsizliyi?** — «Hər şey lokal işləyir, fayl yaddaşda emal olunur, orijinal saxlanmır, GPS göstərilmir.»
- **Не знаете ответа:** «Yaxşı sualdır, bunu hələ ölçməmişik — pilotda yoxlayacağıq.»

## Перед выходом
1. Прогнать вслух с таймером 3 раза. Если больше 5:00, сокращать текст, а не демо.
2. Для демо: проверенное ИИ-фото и своё фото с телефона на рабочем столе, приложение открыто, язык AZ.
3. Вписать контакт на последний слайд вместо [əlaqə].
