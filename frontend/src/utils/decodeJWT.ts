export default function decodeJWT(token: string) {
    function base64UrlDecode(base64Url: string) {
        // Base64Url to Base64
        let base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');

        // Pad with '='
        switch (base64.length % 4) {
            case 0:
                break;
            case 2:
                base64 += '==';
                break;
            case 3:
                base64 += '=';
                break;
            default:
                throw 'Invalid base64 string';
        }

        // Decode Base64 string
        return decodeURIComponent(
            atob(base64)
                .split('')
                .map(function(c) {
                    return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
                })
                .join('')
        );
    }

    let [header, payload, signature] = token.split('.');

    // Decode header and payload
    let decodedHeader = JSON.parse(base64UrlDecode(header));
    let decodedPayload = JSON.parse(base64UrlDecode(payload));

    return {
        header: decodedHeader,
        payload: decodedPayload,
        signature: signature
    } as {
        header: {
            alg: string
            typ: string
        }
        payload: {
            token_type: string
            exp: number
            iat: number
            jti: string
            user_id: string
        }
        signature: string
    };
}

