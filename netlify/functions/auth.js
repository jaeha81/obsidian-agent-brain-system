exports.handler = async function(event) {
    if (event.httpMethod !== 'POST') {
          return { statusCode: 405, body: 'Method Not Allowed' };
    }

    try {
          const { password } = JSON.parse(event.body);
          const correct = process.env.BUCKY_AUTH_PASSWORD;

      if (!correct) {
              return {
                        statusCode: 500,
                        body: JSON.stringify({ ok: false, error: 'Server config error' })
              };
      }

      if (password === correct) {
              return {
                        statusCode: 200,
                        headers: {
                                    'Set-Cookie': `bucky_auth=${correct}; Path=/; Max-Age=604800; HttpOnly; SameSite=Strict`,
                                    'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ ok: true })
              };
      } else {
              return {
                        statusCode: 401,
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ ok: false })
              };
      }
    } catch (e) {
          return {
                  statusCode: 400,
                  body: JSON.stringify({ ok: false, error: 'Bad request' })
          };
    }
};
