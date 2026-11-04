# Value Mapping: правила по тегу и области профилей — задача для фронта

Полное описание механизма — в [value_mapping.md](value_mapping.md); здесь только то, что нужно фронту.

## Модель данных

### Профиль

```json
{
  "id": "6f1c…",
  "name": "Standart",
  "integrator": "hoteza",
  "scope": "tenant",
  "room_type": null,
  "device": null,
  "integrations": ["a1b2c3d4-…"],
  "rules": [ … ],
  "created_at": "…",
  "updated_at": "…"
}
```

| Поле           | Запись        | Описание                                                                             |
| -------------- | ------------- | ------------------------------------------------------------------------------------ |
| `name`         | да            | Уникально в отеле                                                                    |
| `integrator`   | да            | Имя интегратора (`hoteza`)                                                           |
| `scope`        | нет           | `tenant` (по умолчанию), `room_type`, `device`                                       |
| `room_type`    | —             | uuid типа комнаты; обязателен при `scope: room_type`, иначе `null`                   |
| `device`       | —             | uuid устройства; обязателен при `scope: device`, иначе `null`                        |
| `rules`        | да            | Все правила профиля; `PUT` заменяет их целиком                                       |
| `integrations` | только чтение | id интеграций, к которым профиль подключён как `mapping_profile` (только у `tenant`) |

### Правило

```json
{
  "tag_names": ["dimmer", "dimmer_2"],
  "external": { "value_type": "integer" },
  "transform": {
    "type": "range",
    "grms": { "min": 0, "max": 255 },
    "external": { "min": 0, "max": 100, "step": 10 }
  },
  "direction": "both",
  "on_invalid": "const",
  "on_invalid_value": 0
}
```

| Поле                  | Обязательно   | Значения                                                                                                            |
| --------------------- | ------------- | ------------------------------------------------------------------------------------------------------------------- |
| `tag_names`           | да            | Непустой список ключей тегов, каждый до 255 символов. Имя не повторяется ни в правиле, ни между правилами профиля   |
| `external.value_type` | да            | `integer`, `number`, `string`, `boolean`                                                                            |
| `transform`           | да            | `enum`, `range`, `linear`, `passthrough` — поля как раньше, см. [value_mapping.md](value_mapping.md#формат-правила) |
| `direction`           | нет, `both`   | `both`, `to_external` (только чтение), `to_grms` (только запись)                                                    |
| `on_invalid`          | нет, `reject` | `reject`, `skip`, `clamp` (только числовой `value_type`), `const`                                                   |
| `on_invalid_value`    | при `const`   | Значение GRMS, которое пишется вместо недопустимого. При других `on_invalid` должно быть `null` или отсутствовать   |

## Как выбирается правило

Одно правило может охватывать несколько тегов. Для тега берётся первое правило, в `tag_names` которого есть его имя, по цепочке:

1. профиль устройства тега (`scope: device`);
2. профиль типа комнаты, где стоит устройство (`scope: room_type`);
3. профиль интеграции (`mapping_profile` интеграции, `scope: tenant`).

Важно для UI:

- Частные профили (`room_type`, `device`) подключать к интеграции не нужно: они действуют на интеграцию своего интегратора в отеле сами.
- Частные профили работают, **только пока у интеграции есть `mapping_profile`**. «Без профиля» (`null`) выключает маппинг целиком.
- В частном профиле достаточно правил, которые отличаются от профиля интеграции.
- Частный профиль может заменить правило, но не отменить его. Тег без правила во всей цепочке идёт как есть.
- На одну цель (тип комнаты или устройство) у интегратора в отеле — один профиль.

## Эндпоинты

Все под `/api/v1/services/`, JWT, только данные отеля пользователя (чужое — 404).

| Метод и путь                    | Что делает                                             | Право                   |
| ------------------------------- | ------------------------------------------------------ | ----------------------- |
| `GET mapping-profiles/`         | Список                                                 | `view_mappingprofile`   |
| `POST mapping-profiles/`        | Создать (201)                                          | `add_mappingprofile`    |
| `GET mapping-profiles/<id>/`    | Один профиль                                           | `view_mappingprofile`   |
| `PUT mapping-profiles/<id>/`    | Заменить профиль и все правила                         | `change_mappingprofile` |
| `DELETE mapping-profiles/<id>/` | Удалить (204); у интеграций `mapping_profile` → `null` | `delete_mappingprofile` |
| `PUT integration/<id>/`         | Поле `mapping_profile`: id профиля `tenant` или `null` | `change_integration`    |

Параметры списка: `page`, `size` (по умолчанию 50, максимум 500), `search` (подстрока в `name`), `integrator`, `scope`, `sort_by`.

Полезные запросы:

- профили для выбора в карточке интеграции: `GET mapping-profiles/?integrator=hoteza&scope=tenant`;
- частные профили интегратора: `GET mapping-profiles/?integrator=hoteza&scope=device` (или `room_type`);
- подсказки `tag_names` для профиля устройства: `GET device/<device_id>/tag-types/` — теги устройства из `TAG_TYPES`.

## Ошибки 400

| Ситуация                                                     | Ответ                                                                                 |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------------- |
| Имя занято                                                   | `{"name": ["A mapping profile with this name already exists."]}`                      |
| Нет цели для области                                         | `{"device": ["Required for the device scope."]}`                                      |
| Лишняя цель                                                  | `{"room_type": ["Must be empty for the tenant scope."]}`                              |
| На эту цель у интегратора уже есть профиль                   | `{"device": ["The integrator already has a profile for it."]}`                        |
| Имя тега в двух правилах или дважды в одном                  | `{"rules": ["Duplicate tag names: ['dimmer']."]}`                                     |
| Пустой `tag_names`                                           | `{"rules": [{"tag_names": ["This list may not be empty."]}, {}]}`                     |
| Пустое имя в `tag_names`                                     | `{"rules": [{"tag_names": {"0": ["This field may not be blank."]}}, {}]}`              |
| Ошибка в одном правиле (по индексу в `rules`)                | `{"rules": [{"non_field_errors": ["on_invalid const needs on_invalid_value."]}, {}]}` |
| `PUT`: профиль подключён к интеграции другого интегратора    | `{"integrator": ["The profile is used by another integrator."]}`                      |
| `PUT`: подключённый профиль переводят в `room_type`/`device` | `{"scope": ["The profile is used by integrations: it stays tenant."]}`                |
| `PUT integration/<id>/` с профилем другого интегратора       | `{"mapping_profile": ["The profile belongs to another integrator."]}`                 |
| `PUT integration/<id>/` с профилем `room_type`/`device`      | `{"mapping_profile": ["Only a tenant profile can be attached."]}`                     |

## Экраны

1. **Список профилей.** Колонки: `name`, `integrator`, область (для `room_type`/`device` — название цели), число правил. Фильтры: интегратор, область; поиск; сортировка. При удалении профиля `tenant` с непустым `integrations` предупредить: интеграции начнут отдавать значения GRMS, а частные профили перестанут действовать.
2. **Редактор профиля.**
   - Шапка: `name`, `integrator`, переключатель области; для `room_type` — выбор типа комнаты, для `device` — выбор устройства. Если `integrations` не пуст, область менять нельзя (заблокировать переключатель).
   - Список правил, сохранение одним `PUT` со всеми правилами.
   - `tag_names` — мультиселект с вводом своих значений и подсказками; имена, занятые другими правилами профиля, не предлагать. В списке правил показывать имена через запятую.
   - `on_invalid`: `clamp` показывать только для числового `value_type`; при `const` показывать обязательное поле `on_invalid_value` и очищать его при выборе другого варианта.
   - Ошибки правил — у правила по индексу.
   - Для частного профиля подсказка: «Правила этого профиля заменяют правила профиля интеграции для тех же тегов».
3. **Карточка интеграции.** Выбор `mapping_profile` из профилей `tenant` того же интегратора, вариант «Без профиля» = `null`. Ниже — частные профили интегратора (ссылки на редактор) с пометкой, что они действуют, только пока выбран профиль.
4. **Карточка устройства / типа комнаты** (опционально). Ссылка «Профиль маппинга» на профиль с этой целью или кнопка «Создать», предзаполняющая `scope` и цель.
