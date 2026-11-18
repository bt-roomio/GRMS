# Global Settings для фронтенда

Всё, что нужно, чтобы собрать экраны шаблонов глобальных настроек: какие запросы посылать, что
приходит в ответ, как собирать фильтры и какие грабли есть.

Серверная механика (как шаблон пишется в атрибуты, как уходит на устройства, как считается статус)
описана в [`global-settings.md`](global-settings.md) — здесь на неё есть ссылки.

## Содержание

1. [Старт и карта экранов](#1-старт-и-карта-экранов)
2. [Общие правила API и права](#2-общие-правила-api-и-права)
3. [Шаблоны](#3-шаблоны)
4. [Страница комнат](#4-страница-комнат)
5. [Применение шаблона](#5-применение-шаблона)
6. [TypeScript-типы и клиент](#6-typescript-типы-и-клиент)
7. [Грабли и чеклист приёмки](#7-грабли-и-чеклист-приёмки)

---

## 1. Старт и карта экранов

**Базовый URL** — `https://<api-host>/api/v1/main/global-settings/`. Токен — обычный JWT
(`POST /api/v1/users/access-token/`), заголовок `Authorization: Bearer <access>`.

**Swagger** — `/api/v1/swagger/`, тег `Main, Global Settings`.

| Экран / элемент | Что показывает | Эндпоинты |
| --- | --- | --- |
| **Список шаблонов** | Таблица: имя, сколько раз применяли, дата изменения | `GET templates/` |
| **Редактор шаблона** | Имя + редактор `config` | `GET/POST templates/`, `GET/PUT/DELETE templates/<id>/` |
| **Страница комнат** | Комнаты с устройствами: фильтры, устройство и шаблон со статусом | `GET rooms/` |
| **Диалог применения** | Выбрать шаблон и применить к отмеченным комнатам | `GET templates/`, `POST apply-preset/` |

Минимальный объём, который уже полезен: список шаблонов + редактор + страница комнат с выбором и
кнопкой «Применить».

---

## 2. Общие правила API и права

### 2.1. Ошибки

`400` — ошибки валидации в формате DRF, показывайте их у соответствующего поля:

```json
{"name": ["Global settings template with name 'Default' already exists."]}
```

`403` — нет прав, `404` — шаблона нет (или он другого тенанта).

### 2.2. Пагинация

Только у списка шаблонов: `page` (с `1`) и `size` (`1`–`200`, по умолчанию `50`). Ответ
`{"count": N, "results": [...]}`, страниц — `Math.ceil(count / size)`.

Страница комнат **не постраничная**: приходит массив всех комнат под фильтром.

### 2.3. Повторяющиеся параметры

`sort_by`, `blocks` (и при желании `room_types`) передаются **повтором ключа**:

```text
?blocks=1:1,2&blocks=2&sort_by=-used
```

Axios по умолчанию шлёт массивы как `blocks[]=...` — сервер такое **не прочитает**. Нужен
`paramsSerializer` или `URLSearchParams` с `append()` (см. [6.2](#62-клиент)).

### 2.4. Права и видимость элементов

| Действие | Право |
| --- | --- |
| Видеть список и шаблоны | `main.view_globalsettingstemplate` |
| Кнопка «Создать» | `main.add_globalsettingstemplate` |
| Кнопка «Сохранить» в редакторе | `main.change_globalsettingstemplate` |
| Кнопка «Удалить» | `main.delete_globalsettingstemplate` |
| Страница комнат | `main.view_room` + `main.view_globalsettingstemplate` |
| Кнопка «Применить» | `main.view_globalsettingstemplate` + `shuttle.add_attributerpc` |

Все права есть у роли `TENANT_ADMIN`. Прячьте кнопки по правам пользователя, но всё равно
обрабатывайте `403`.

---

## 3. Шаблоны

### 3.1. Список

```http
GET /api/v1/main/global-settings/templates/?search_field=name&search_value=res&sort_by=-used&page=1&size=50
```

| Параметр | Значения |
| --- | --- |
| `search_field` | Только `name` |
| `search_value` | Подстрока, регистр не важен |
| `sort_by` | `created_at`, `-created_at` (по умолчанию), `name`, `-name`, `used`, `-used` |

Колонки таблицы: `name`, `used` («Применён N раз»), `updated_at`. `used` растёт на 1 за каждое
применение, не за каждую комнату.

### 3.2. Создание и редактирование

```http
POST /api/v1/main/global-settings/templates/
{"name": "Default hotel", "config": {"timezone": 5, "guest_auto_block": true}}
```

```http
PUT /api/v1/main/global-settings/templates/<id>/
{"name": "Default hotel", "config": {"timezone": 3}}
```

- `name` обязателен **и в `POST`, и в `PUT`**. Всегда отправляйте имя из формы.
- `config` можно не отправлять в `PUT`, если его не меняли. Так у комнат не сбросится статус
  `up_to_date` (см. [3.3](#33-что-делает-изменение-config)).
- Имя уникально в тенанте **без учёта регистра** и обрезается по краям: `" default "` и `Default` —
  одно имя.
- `config` — только JSON-объект. Массив или строка → `400 Config must be a JSON object.`
- `used`, `config_updated_at`, `created_at`, `updated_at` — только для чтения.

### 3.3. Что делает изменение `config`

Изменение `config` **не отправляется на устройства само**. Оно только переводит все комнаты с этим
шаблоном в статус `outdated`. Чтобы настройки дошли до устройств, шаблон нужно применить заново.

Переименование статус не меняет.

После сохранения изменённого `config` стоит показать подсказку: «Шаблон изменён. Примените его
заново к комнатам, чтобы обновить устройства» и ссылку на страницу комнат с поиском этих комнат.

### 3.4. Удаление

`DELETE templates/<id>/` → `204`. Устройства не меняются: комнаты, где он стоял, будут показывать
`status: "deleted"`. Перед удалением спросите подтверждение и предупредите об этом.

### 3.5. Редактор `config`

- **Типы значений важны**: устройство получает то, что лежит в JSON. `true` ≠ `"true"`, `5` ≠ `"5"`.
  Если поле редактора — `<input>`, приводите значение к нужному типу перед отправкой.
- **Целые и дробные**: в JS `22.0` сериализуется как `22`, на сервере это станет целым (`long_v`).
  Если устройству нужен дробный тип, значение должно быть действительно дробным (`22.5`).
- **`null` игнорируется**: ключ со значением `null` не будет записан на устройства. Не используйте
  `null` как «сбросить».
- **Удалённый ключ остаётся на устройствах.** Если убрать ключ из шаблона и применить заново,
  у устройств останется старое значение. Об этом стоит предупредить в редакторе.

---

## 4. Страница комнат

### 4.1. Запрос

```http
GET /api/v1/main/global-settings/rooms/?room_types=<id1>,<id2>&blocks=1:1,2&blocks=2&search_field=number&search_value=10
```

Ответ — массив, отсортирован по блоку, этажу, номеру:

```json
[
  {
    "id": "5e1f2a3b-...",
    "number": "101",
    "floor": "1",
    "block": "A",
    "room_type": {"id": "7a8b9c0d-...", "title": "Standard"},
    "device": {"id": "2b3c4d5e-...", "name": "RCU-101"},
    "template": {"id": "9b0c7e2a-...", "name": "Default hotel", "status": "up_to_date"}
  }
]
```

`room_type` и `template` могут быть `null`. Комнаты без активных устройств сервер не
возвращает, поэтому `device` есть всегда: отдельное состояние «нет устройства» рисовать не нужно.

### 4.2. Фильтр по блокам и этажам

Параметр `blocks` повторяется на каждое правило, правила объединяются через ИЛИ:

| Правило | Что выбирает |
| --- | --- |
| `1:1,2,3` | Блок `1`, этажи `1`, `2`, `3` |
| `2` | Весь блок `2` |
| `:1,2` | Этажи `1` и `2` во всех блоках |

Пустое правило `:` → `400`. Если правил нет, фильтра нет.

Сборка из дерева «блок → этажи» с галочками:

```ts
type BlockSelection = {
  allBlocks: Set<string>;               // блок отмечен целиком
  floors: Map<string, Set<string>>;     // блок → отмеченные этажи
  floorsEverywhere: Set<string>;        // этажи «во всех блоках»
};

function blocksParams(sel: BlockSelection): string[] {
  const rules: string[] = [];
  for (const block of sel.allBlocks) rules.push(block);
  for (const [block, floors] of sel.floors) {
    if (!sel.allBlocks.has(block) && floors.size) rules.push(`${block}:${[...floors].join(",")}`);
  }
  if (sel.floorsEverywhere.size) rules.push(`:${[...sel.floorsEverywhere].join(",")}`);
  return rules;
}
```

Блоки и этажи для дерева берите из самих комнат (первый запрос без фильтров) или из существующего
списка комнат тенанта.

Если имя блока или этажа содержит `:` или `,`, правило не разберётся. Такие значения в фильтре
лучше не предлагать.

### 4.3. Фильтр по типам комнат

`room_types=<id1>,<id2>`, через запятую или повтором ключа. Сочетается с `blocks` через И.

### 4.4. Поиск

`search_field` + `search_value`, только парой:

| `search_field` | Ищет по |
| --- | --- |
| `number` | Номеру комнаты |
| `floor` | Этажу |
| `block` | Блоку |
| `room_type` | Названию типа |
| `device` | Имени **показанного** в строке устройства |

Подстрока, регистр не важен: `floor` + `1` найдёт этажи `1`, `10`, `11`. Для точного выбора этажей
используйте `blocks`. Поиск сочетается с фильтрами через И.

Список не постраничный, поэтому поиск можно делать с debounce ~300 мс прямо по вводу. Не
отправляйте `search_field` без `search_value` (пустая строка ввода = не передавать оба).

### 4.5. Колонка «Шаблон» и статусы

| `template` / `status` | Что показать |
| --- | --- |
| `null` | «—», шаблон не применялся |
| `up_to_date` | Имя шаблона, зелёный бейдж «Актуален» |
| `outdated` | Имя шаблона, жёлтый бейдж «Устарел» + подсказка «Шаблон изменён после применения» |
| `deleted` | «Шаблон удалён», серый бейдж; `name` = `null`, показывать нечего |

`up_to_date` — состояние на сервере, а не подтверждение от устройства: устройство могло быть
офлайн. Не пишите «Применено на устройстве».

Шаблон и статус относятся к **показанному** устройству (колонка `device`).

Полезный быстрый фильтр «Устаревшие»: сервер его не делает, фильтруйте на клиенте по
`template?.status === "outdated"`. Список не постраничный, поэтому это корректно.

---

## 5. Применение шаблона

### 5.1. Запрос

```http
POST /api/v1/main/global-settings/apply-preset/
{"room_ids": ["5e1f2a3b-...", "..."], "template_id": "9b0c7e2a-..."}
```

```json
{"devices": ["2b3c4d5e-...", "..."]}
```

`devices` — все активные устройства выбранных комнат, на которые записан шаблон. Пустой массив
возможен, только если устройства успели деактивировать после загрузки страницы.

### 5.2. Поток в UI

1. Пользователь отмечает комнаты в таблице (чекбоксы + «Выбрать все под фильтром»).
2. Кнопка «Применить шаблон» → диалог со списком шаблонов (`GET templates/?size=200`).
3. Подтверждение: «Применить "Default hotel" к 24 комнатам?».
4. `POST apply-preset/`. Кнопку блокировать на время запроса, чтобы не было двойного применения.
5. Тост по ответу:
   - `devices.length > 0` → «Шаблон отправлен на N устройств»;
   - `devices.length === 0` → «В выбранных комнатах нет устройств» (редкий случай, см. 5.1).
6. Перезапросить `GET rooms/` с теми же фильтрами: у комнат будет новый шаблон со статусом
   `up_to_date`. Атрибуты записаны до ответа, поэтому данные уже свежие.

### 5.3. Что важно сказать пользователю

- Шаблон пишется на **все** активные устройства комнаты, не только на показанное.
- Отправка на устройства асинхронная, подтверждения нет. Если устройство было офлайн, доставка не
  гарантирована, а статус на странице этого не покажет.
- Ключи прошлого шаблона, которых нет в новом, остаются на устройствах.

### 5.4. Ошибки

| Ответ | Что делать |
| --- | --- |
| `400 {"room_ids": ["Rooms not found: <id>, ..."]}` | Комнаты удалили или деактивировали. Обновить список и снять выбор. Ничего не применено |
| `400 {"template_id": ["Global settings template not found."]}` | Шаблон удалили. Обновить список шаблонов в диалоге |
| `400 {"room_ids": ["This list may not be empty."]}` | Не давать нажать «Применить» без выбора |
| `403` | Нет `shuttle.add_attributerpc`. Кнопку стоило спрятать |

---

## 6. TypeScript-типы и клиент

### 6.1. Типы

```ts
export interface GlobalSettingsTemplate {
  id: string;
  name: string;
  config: Record<string, unknown>;
  used: number;
  config_updated_at: string; // ISO 8601
  created_at: string | null;
  updated_at: string | null;
}

export interface GlobalSettingsTemplatePayload {
  name: string;
  config?: Record<string, unknown>; // в PUT можно не передавать
}

export interface Paginated<T> {
  count: number;
  results: T[];
}

export type TemplateStatus = "up_to_date" | "outdated" | "deleted";

export interface GlobalSettingsRoom {
  id: string;
  number: string;
  floor: string;
  block: string;
  room_type: { id: string; title: string } | null;
  device: { id: string; name: string }; // rooms without devices are not returned
  template: { id: string; name: string | null; status: TemplateStatus } | null;
}

export type RoomSearchField = "number" | "floor" | "block" | "room_type" | "device";

export interface GlobalSettingsRoomFilters {
  room_types?: string[];
  blocks?: string[]; // правила "1:1,2" | "2" | ":1,2"
  search_field?: RoomSearchField;
  search_value?: string;
}

export interface ApplyTemplatePayload {
  room_ids: string[];
  template_id: string;
}

export interface ApplyTemplateResponse {
  devices: string[];
}
```

### 6.2. Клиент

```ts
const BASE = "/api/v1/main/global-settings";

function toQuery(params: Record<string, string | number | string[] | undefined>): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === "") continue;
    if (Array.isArray(value)) value.forEach((item) => query.append(key, item));
    else query.set(key, String(value));
  }
  return query.toString();
}

export const globalSettingsApi = {
  listTemplates: (params: { search_value?: string; sort_by?: string[]; page?: number; size?: number }) =>
    http.get<Paginated<GlobalSettingsTemplate>>(
      `${BASE}/templates/?${toQuery({ ...params, search_field: params.search_value ? "name" : undefined })}`,
    ),
  getTemplate: (id: string) => http.get<GlobalSettingsTemplate>(`${BASE}/templates/${id}/`),
  createTemplate: (body: GlobalSettingsTemplatePayload) =>
    http.post<GlobalSettingsTemplate>(`${BASE}/templates/`, body),
  updateTemplate: (id: string, body: GlobalSettingsTemplatePayload) =>
    http.put<GlobalSettingsTemplate>(`${BASE}/templates/${id}/`, body),
  deleteTemplate: (id: string) => http.delete(`${BASE}/templates/${id}/`),

  listRooms: ({ search_field, search_value, ...filters }: GlobalSettingsRoomFilters) =>
    http.get<GlobalSettingsRoom[]>(
      `${BASE}/rooms/?${toQuery({
        ...filters,
        // only as a pair, otherwise the API answers 400
        ...(search_field && search_value ? { search_field, search_value } : {}),
      })}`,
    ),

  apply: (body: ApplyTemplatePayload) => http.post<ApplyTemplateResponse>(`${BASE}/apply-preset/`, body),
};
```

`http` — ваш axios/fetch-клиент с токеном. Query-строка собрана вручную, поэтому настройки
`paramsSerializer` не нужны.

---

## 7. Грабли и чеклист приёмки

### 7.1. Грабли

| Грабли | Как избежать |
| --- | --- |
| Axios шлёт `blocks[]=...` | Собирать query через `URLSearchParams.append` |
| `PUT` без `name` → `400` | Всегда отправлять имя |
| Изменение `config` «не применилось» | Оно и не должно: комнаты стали `outdated`, нужно применить заново |
| `22.0` уходит как целое | Хранить дробные значения как действительно дробные или как строку, если прошивка это ожидает |
| `null` в `config` ничего не сбрасывает | Не использовать `null` как значение настройки |
| Поиск `floor=1` находит `10`, `11` | Для точного выбора этажей — `blocks=:1` |
| Двойное применение по двойному клику | Блокировать кнопку на время запроса |
| `search_field` без `search_value` → `400` | Передавать только парой |

### 7.2. Чеклист

- [ ] Список шаблонов: поиск по имени, сортировка по имени/использованию/дате, пагинация.
- [ ] Создание шаблона без `config` работает, дубль имени показывает ошибку у поля.
- [ ] Переименование не меняет статус комнат; изменение `config` делает их `outdated`.
- [ ] Удаление спрашивает подтверждение, комнаты показывают «Шаблон удалён».
- [ ] Фильтр по блокам/этажам: весь блок, этажи в блоке, этажи во всех блоках, комбинации.
- [ ] Фильтр по типам комнат и поиск по пяти полям; всё вместе сочетается через И.
- [ ] Колонка «Шаблон» показывает все четыре состояния (`null`, `up_to_date`, `outdated`, `deleted`).
- [ ] Применение: подтверждение, блокировка кнопки, тост по `devices.length`, перезапрос комнат.
- [ ] Кнопки скрыты без прав, `403` обработан.
