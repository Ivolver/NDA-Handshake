# NDA Handshake Confirmation

NDA Handshake Protocol, version 0.7

The person named in the confirmation block of a company's nda-handshake.md file (the "File") gives this Confirmation on behalf of the company named in that File (the "Company").

1. **Standing approval.** The Company approves, in advance, every mutual non-disclosure agreement that the NDA Handshake Protocol, version 0.7 (the "Protocol"), produces from the File and a counterparty's file with a result of AGREED. The Company executes each such agreement as set out in section 5. No further signature or approval is needed, and none will be given.

2. **Limits.** This approval covers only an agreement that meets every one of these conditions:

   - it is on a standard form listed in the File;
   - each of its terms results from applying the Protocol's rules to the File and the counterparty's file, and is within the positions stated in the File;
   - it results from a handshake that a person at the Company started or approved;
   - the positions in the File are the positions this Confirmation was given for.

   The Company is not bound under this Confirmation to anything else. If a position in the File changes, this Confirmation no longer applies until it is given again for the changed File.

3. **Authority.** The person giving this Confirmation represents that they have authority to bind the Company to non-disclosure agreements and to give this approval, and that the Company has obtained any internal approval its governing documents require.

4. **Electronic agent.** Any software that applies the Protocol's rules to the File and a counterparty's file acts as the Company's electronic agent for the purposes of the Uniform Electronic Transactions Act, the federal E-SIGN Act and any similar law. The electronic agent is a tool the Company uses. It is not a party and has no authority of its own. Every act it performs under this Confirmation is the act of the Company, taken on the Company's instructions as stated in the File.

5. **How an agreement is formed.** Each agreement is formed by the Protocol's sealed exchange:

   - **Invitation.** An invitation states the purpose and carries a commitment to the inviting party's file, being a fingerprint of that file taken together with a secret value. The invitation is not an offer.
   - **Offer.** A reply that attaches the replying party's file is an offer to enter into the non-disclosure agreement that the Protocol produces from that file and the file the inviting party committed to.
   - **Acceptance.** The inviting party's later message attaching its own file, the secret value and a statement of the terms hash, the fingerprint of each file and the Protocol version (the "Receipt") is acceptance of that agreement, if the Protocol's result on the two files is AGREED. The agreement is formed and executed by both parties when that message is sent. This applies whether the Company is the inviting party or the replying party.
   - **Check.** The replying party is to run the Protocol on the two files promptly, and in any event within one business day after receiving the acceptance (the "Check Period"). Within the Check Period it may contest the agreement by notice to the other party, but only on one of these grounds: its own run produces a different terms hash or a result other than AGREED; the inviting party's file and secret value do not match the commitment; the Receipt misstates the fingerprint of either file or the date of the acceptance; or the acceptance did not come from the email address, or an address at the email domain, stated in the inviting party's file.
   - **Effect of a contest.** If the agreement is validly contested, no agreement is formed under this Confirmation. Information disclosed before the contest in reliance on the acceptance remains protected as Confidential Information on the terms stated in the acceptance.
   - **No contest.** If the Company, as the replying party, does not contest within the Check Period, the agreement identified by the Receipt is final, and the Company waives any objection based on a mismatch or error that running the Protocol would have shown. This paragraph binds the Company only to terms that are within the positions stated in the File.
   - **Altered file.** The preceding paragraph does not apply if the fingerprint the Receipt states for the Company's file is not the fingerprint of the file the Company sent. The Company is not bound through a file it did not issue.
   - **Security procedure.** The terms hash and the file fingerprints are a security procedure agreed between the parties for detecting changes or errors, for the purposes of section 10 of the Uniform Electronic Transactions Act and any similar law.

6. **Signature.** The Company adopts as its signature on each agreement the mark "/s/" followed by the Company's legal name, applied under this Confirmation and shown with the name of the person who gave this Confirmation and its date. Either party's software may apply that mark to a copy of the agreement for both parties.

7. **The Company's File.** The File is the nda-handshake.md sent from the email address, or from an address at the email domain, stated in its confirmation block. The version that applies to a handshake is the one whose fingerprint is recorded in that handshake.

8. **Reliance.** A counterparty may rely on this Confirmation. The Company will not contest the validity or enforceability of an agreement formed within these limits, or its attribution to the Company, on the ground that no individual reviewed or signed it.

9. **Records.** The Company will keep the handshake record for each agreement, including the terms hash and both file fingerprints. A copy of each agreement is to be sent to the notices address stated in the File.

10. **Withdrawal.** The Company may withdraw this Confirmation at any time by removing the confirmation block from the File. Withdrawal applies to handshakes sealed afterwards and does not affect any agreement already formed.

11. **Governing law.** This Confirmation is governed by the law of the state in which the Company is formed.
