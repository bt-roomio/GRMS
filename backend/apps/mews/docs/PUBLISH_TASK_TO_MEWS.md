# 1. Давай реализовать отправить запрос в Mews в файле @apps/mews/signals.py publish_mur_relay_to_mews

"
Если ts_kv_latest.key == 'MUR Relay' и ts_kv_latest.get_value() == '1' и ts_kv_latest.entity.room.guest.additional_info.mews_mur_relay <= datetime.now() + timedelta(minutes=3)

ClientToken и AccessToken ты можешь брать TsKvLatest.entity.tenant_id
Client пусть будет так
ServiceOrderId ты возмешь из TsKvLatest.Entity.Room.Guest.additional_info.mews_reservation_id
Name: Константа MUR Rela
DeadlineUtc: Сутка
Вот пример.

curl --location '<https://api.mews-demo.com/api/connector/v1/tasks/add>' \
 --header 'Content-Type: application/json' \
 --header 'Cookie: \_\_cf_bm=wUfE9did4t0Bp.6flR1301fKrvOHKSc_GbhRSM6tB4E-1764601144-1.0.1.1-WzCe_uw8UhpMBzcGVJ1HlvlukiaqRcQ4V89zdX8OydBNmwjTYnKhU0a1wnOWzdVu.e.\_hGnblIT9PMvx8I.v2BSoKCWCKvM8cl27gEUlp3g;
\_cfuvid=uRNHYcUd.vVEaKCzwjwQCFKGtAs8a6aQBZF2QVpJ4ic-1764595934835-0.0.1.1-604800000' \
 --data '{
"ClientToken": "E916C341431C4D28A866AD200152DBD3-A046EB5583FFBE94DE1172237763712",
"AccessToken": "1AEFA58C55E74D65BDC7AD2001564C12-66633E0B736F523379B9E5966165A55",
"Client": "Mews Web Commander 9221.0.0",

      "ServiceOrderId": "08d72a94-67e7-4bf8-b990-b3a600eba133",
      "Name": "Test2",
      "DeadlineUtc": "2025-12-2T00:00:00Z"

}'
"
