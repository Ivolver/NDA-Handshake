# NDA Handshake guide

This plugin teaches your assistant how to use NDA Handshake, an open protocol that lets two companies' assistants put a standard mutual NDA in place over three emails, with no redlines and no signature round.

It contains one skill and nothing else. It runs no program, starts no server and installs nothing.

## What it does

- Tells the assistant when a request or an email is an NDA Handshake matter, and how to handle it step by step.
- Tells the assistant the rules that keep a handshake safe: read only the labelled block in an email, never give a company's confirmation itself, never bargain with the other side's assistant.
- If the NDA Handshake connector is not available, tells the assistant how to explain that plainly.

## Install

In Claude Code:

    /plugin install nda-handshake-guide --marketplace Ivolver/NDA-Handshake

In the Claude desktop app, add the repository `Ivolver/NDA-Handshake` under Customize, Plugins, and choose the guide.

## What it needs

The work of a handshake is done by the NDA Handshake connector, a small open-source program that runs on your own computer. This plugin does not include it. You add the connector yourself, from the project's releases page:

https://github.com/Ivolver/NDA-Handshake/releases

In the Claude desktop app it installs as a one-click extension. Without the connector, the assistant can explain NDA Handshake and help you decide whether to use it, but it cannot carry out a handshake.

## Privacy

This plugin collects nothing and sends nothing. It is a set of written instructions for the assistant.

When you run a handshake with the connector, your company's file and your completed NDAs stay on your own computer. Nothing is sent to the publisher of this plugin or to any server. A handshake shares your company's NDA positions with the counterparty you choose, by email, through your own mail tool, and your assistant asks before replying to an invitation. Full details are in the project's privacy section:

https://github.com/Ivolver/NDA-Handshake#privacy

## Not legal advice

NDA Handshake is a tool for putting a standard agreement in place. It is not legal advice and creates no attorney-client relationship. Have your own counsel review your positions and the confirmation text before you rely on it.

## License

Apache License 2.0. See LICENSE.
