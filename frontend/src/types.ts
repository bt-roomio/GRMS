interface ILocales {
    name: string
    code: string
    icon: string
}

interface ITab {
    name: string
    to: string
}

interface Item {
    icon: string;
    name: string;
    to: string;
    children?: { icon: string; to: string; name: string; }[];
}