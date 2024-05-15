interface IEmailSetup {
    tenant: string,
    email: string,
    host: string,
    username: string,
    password: string,
    port: string,
    use_tls: boolean
}
interface IGeneralSetting {
    lang: string,
    timezone: number,
    controllers_sync: boolean,
    check_in_out: boolean,
    vip_status: boolean,
    suite_rooms_controls_sync: boolean,
    laundry: boolean,
    visionline: boolean,
    opera_integration: boolean,
    visionline_card_system: boolean,
    aperio_locks: boolean,
    door_lock: {
        ving_card: boolean,
        kaba: boolean
    },
    auto_checkout: boolean
}